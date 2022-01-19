#%%
#smparser-classes.py

import csv
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import imghdr
import json
import logging
from pathlib import Path
import platform
import re
from types import SimpleNamespace
import zipfile

import cv2
import face_recognition
import scrubadub
#import pysimplegui as sg
#%%
class SMParser():
	def __init__(self, person_name, person_alias, zip_path, home_dir=None):
		self.VALID_TYPES = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tiff', '.tif']
		self.zip_file = zipfile.ZipFile(zip_path)
		self.zip_root = zipfile.Path(self.zip_file)
		self.person_name = person_name
		self.person_alias = person_alias
		self.ask_date()
		self.sys_check()

		self.home_path = Path(home_dir) if home_dir is not None else Path(zip_path).parent
		self.temp_path = self.home_path / 'TEMP'
		self.temp_path.mkdir(parents=True, exist_ok=True)
		self.outbox_path = self.home_path / 'outbox'
		self.media_path = self.outbox_path / 'media'
		self.media_path.mkdir(parents=True, exist_ok=True)
		self.file_mapping = {}  #{fcsv: {fjson: relpath, fnparse:_, header:[,]}, csvfile2:...}

	def sys_check(self):
		self.timetype = 1 if platform.system() == 'Windows' else -1
		self.time_string_opts = {
			1: lambda ts: ts.strftime("%#I:%M %p"),
			-1: lambda ts: ts.strftime("%-I:%M %p")
		}
		return True

    #Unip and locate files
	def unzip(self):
		'''This code will take advantage of the zipfile context managers
			and open files WITHOUT extracting the entire archive'''
		pass
		return None
        
	def detect_files(self):
		test = all([f.isfile() for f in self.json_files])
		return test

    #Utility Functions
	def ask_date(self):
		'''TODO: Launch a date picker with pysimplegui'''
		self.months_back = 24
		self.last_time = datetime.today()
		self.first_time = self.last_time - relativedelta(months=self.months_back)
		return None
        
	def in_date_range(self, check_date):
		'''Accepts a Date object, returning boolean'''
		return self.first_time <= check_date <= self.last_time
        
	def get_json(self, folder, filename):
		'''Retrieves json file and returns an object'''
		json_path = self.zip_root / folder / f"{filename}.json"
		return json.loads(json_path.read_text(), object_hook=lambda d:SimpleNamespace(**d))
    
	def get_image(self, folder, filename):
		'''File path relative to ziproot'''
		image_path = self.zip_root / folder / filename
		return image_path.read_bytes()

	def parse_img_ext(self, mediafp):
		ext_type = mediafp.suffix 
		return ext_type if ext_type in self.VALID_TYPES else False
			
	def blur_faces(self, img_data):
		'''Detect the faces in an image & apply blur effect over each'''
		#img = cv2.imread(img_path)
		faces = face_recognition.face_locations(img_data)
		logging.debug(f'Blurring {len(faces)} faces')
		for (top, right, bottom, left) in faces:
			face_image = img_data[top:bottom, left:right]
			img_data[top:bottom, left:right] = cv2.GaussianBlur(face_image, (99, 99), 30)
		return img_data

	def scrub_and_save_media(self, media_list):
		'''Cycle through all media, anonymizing each by blurring faces'''
		for ph in media_list:
			photo_bytes = ph.fpsrc.read_bytes()
			photo_data = cv2.imread(photo_bytes)
			img = self.blur_faces(photo_data)
			if img is None: return False
			if not ph.Path.parent.is_dir(): ph.Path.parent.mkdir(parents=True, exist_ok=True)
			cv2.imwrite(ph.Path, img)
		return True

	def genCSV(self, csv_name, header, data):
		'''Generate CSV files from data (a list of dicts)'''
		logging.debug(f'Creating the file {csv_name}')
		csv_out = self.outbox_path / f'{csv_name}.csv'
		with open(csv_out, "w+", encoding='utf-8') as csv_file:
			csv_writer = csv.DictWriter(csv_file, fieldnames=header, extrasaction='ignore')
			csv_writer.writeheader()
			for entry in data:
				csv_writer.writerow(entry)
		return None
    
	@staticmethod
	def clean_text(text):
		text = scrubadub.clean(text)
		return re.sub(r'@\S*', "{{USERNAME}}", text).encode('latin1', 'ignore').decode('utf8', 'ignore')
			
	def time_string(self, timestamp):
		return self.time_string_opts[self.timetype](timestamp)
		
	def parse_time(self, when):
		'''in: a form of date-time
		out: timestamp, time, date'''
		try:
			if when is None:
				ts = datetime.today()
			elif type(when) == int: 
				ts = datetime.fromtimestamp(when)
			else:
				when = when.split("+", 1)[0]
				ts = datetime.strptime(when, '%Y-%m-%dT%H:%M:%S')
		except ValueError:
			print("ValueError: wasn't able to parse timestamp {0}".format(when))
			ts = datetime.today()
		finally:
			date = ts.date()
			time = self.time_string(ts)
		return ts, date, time
#%%	    
@dataclass
class Media():
	fp_src: str
	file_type: str
	Date: str
	Time: str
	Path: str
	Caption: str = ""
	Likes: str = ""
	Comments: str = ""

#Parse Functions unique to each platform
class FBParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass
        
class IGParser(SMParser):
	'''Social Media Parser class for Instagram, v2 Schema'''
	#def __init__(self, person_name, person_alias, zip_path, home_dir=None):
		#pass
    
	def parse_profile_metadata(self):
		logging.info('Parsing IG profile metadata')
		data = self.get_json('account_information','personal_information')
		self.username = data.profile_user[0].string_map_data.Username.value
		return None
	
	def parse_comments(self):
		logging.info("Parsing IG comments")
		data = self.get_json("comments", "post_comments")
		comments_header = ["Date", "Time", "Content"]
		users_comments_on_own_post = []
		users_comments_on_other_post = []

		for comment in data.comments_media_comments:
			c0 = comment.string_list_data[0]
			ts = c0.timestamp
			comment_value = c0.value
			author = comment.title
			timestamp, date, time = self.parse_time(ts)
			
			if not self.in_date_range(timestamp): continue
			content = self.clean_text(comment_value)
			if re.compile(r'^\s*$').match(content): continue
			row = {"Date":date, "Time":time, "Content":content}
			if author == self.username:
				#if users_comments_on_own_post[-1][2] == content: continue
				users_comments_on_own_post.append(row)
			else:
				#if users_comments_on_other_post[-1][2] == content: continue
				users_comments_on_other_post.append(row)
		self.genCSV("users_comments_on_own_post", comments_header, users_comments_on_own_post)
		self.genCSV("users_comments_on_other_post", comments_header, users_comments_on_other_post)

	def parse_follow(self):
		logging.info("Parsing IG Follow")
		data = self.get_json('followers_and_following', 'followers')
		data2 = self.get_json('followers_and_following', 'following')
		follow_header = ['Followers', 'Following']
		payload = [
			{'Followers': len(data.relationships_followers), 
			'Following': len(data2.relationships_following)}]
		self.genCSV("follow", follow_header, payload)

	def valid_post(self, post):
		if hasattr(post, 'creation_timestamp'):
			pts = post.creation_timestamp
		elif hasattr(post.media[0], 'creation_timestamp'):
			pts = post.media[0].creation_timestamp
		else:
			return True
		return self.in_date_range(datetime.fromtimestamp(pts))

	def parse_posts(self):
		logging.info("Parsing IG posts")
		posts_header = ["Date", "Time", "Path", "Caption", "Likes", "Comments"]
		self.posts_rows = []
		#--- PHOTOS
		posts_data = self.get_json("content", "posts_1")
		#jposts[0].media[0].uri, .creation_timestamp, .title
		valid_posts = [p for p in posts_data if self.in_date_range(datetime.fromtimestamp(p.creation_timestamp))]
		for i, post in enumerate(valid_posts):
			for j, photo in enumerate(post.media):
				img_ext = self.parse_ext(photo.uri)
				outpath = self.media_path / f'Post{i}' / f'Photo{chr(97+j)}'
				ts, date, time = self.parse_time(post.creation_timestamp)
				ph = Media(photo.uri, img_ext, date, time, outpath, post.title)
				self.posts_media.append(ph)

		#--- STORIES
		logging.info("Parsing IG stories")
		stories_data = self.get_json("content", "stories")
		#sposts.ig_stories[0].uri
		valid_stories = [s for s in stories_data.ig_stories if self.in_date_range(datetime.fromtimestamp(s.creation_timestamp))]
		for i, story in enumerate(valid_stories):
				img_ext = self.parse_ext(story.uri)
				outpath = self.media_path / f'Story{i}' / f'Photo{chr(97+i)}'
				ts, date, time = self.parse_time(story.creation_timestamp)
				ph = Media(story.uri, img_ext, date, time, outpath, story.title)
				self.posts_media.append(ph)

		#--- PROFILE PICS
		logging.info("Parsing IG profile pic")
		profile_pic_data = self.get_json("content", "profile_photos")
		#prof.ig_profile_picture[0].uri
		for i, photo in enumerate(profile_pic_data.ig_profile_picture):
			img_ext = self.parse_ext(photo.uri)
			outpath = self.media_path / f'Profile' / f'Photo{chr(97+i)}'
			ts, date, time = self.parse_time(photo.creation_timestamp)
			ph = Media(photo.uri, img_ext, date, time, outpath, photo.title)
			self.posts_media.append(ph)
		logging.debug(self.posts_media)
		posts_row_data = [r.__dict__ for r in self.posts_media]
		self.genCSV("posts", posts_header, posts_row_data)
		return None

	def parse_IG_data(self):
		self.parse_profile_metadata()
		self.parse_follow()
		self.parse_comments()
		self.parse_posts()
		if input('Save images?') == 'Y':
			self.scrub_and_save_media(self.posts_media)

class TTParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass    

class YTParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass    
#%%
def main():
	zp = r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\inbox\instagram_test1.zip'
	IG = IGParser('Meg Nesi', 'MN', zp)
	IG.parse_IG_data()

if __name__ == "__main__":
	main()