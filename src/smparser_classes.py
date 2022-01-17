#%%
#smparser-classes

#from collections import namedtuple
import csv
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import imghdr
import json
import logging
from pathlib import Path
import re
from types import SimpleNamespace
import zipfile

#import cv2
#import face_recognition
#import scrubadub
#import pysimplegui as sg
#%%
def gist_json_object():
    data = '{"name":"John Smith","Hometown":{"name":"New York","id":123}}'
    x = json.loads(data, object_hook=lambda d:SimpleNamespace(**d))
    print(x.name, x.hometown.name, x.hometown.id)
    return x

class SMParser():
	def __init__(self, person_name, person_alias, zip_path, home_dir=None):
		self.VALID_TYPES = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tiff', '.tif']
		self.zip_file = zipfile.ZipFile(zip_path)
		self.zip_root = zipfile.Path(self.zip_file)
		self.person_name = person_name
		self.person_alias = person_alias    #TODO: need to create UUID? Answer: No, just allow for User to Input
		self.ask_date()
		self.sys_check()

		self.home_path = Path(home_dir) if home_dir is not None else Path(zip_path).parent
		self.temp_path = self.home_path / 'TEMP'
		self.temp_path.mkdir(parents=True, exist_ok=True)
		self.outbox_path = self.home_path / 'outbox'
		self.outbox_path.mkdir(parents=True, exist_ok=True)
		self.file_mapping = {}  #{fcsv: {fjson: relpath, fnparse:_, header:[,]}, csvfile2:...}

    #Unip and locate files
	def unzip(self):
		'''This code will take advantage of the zipfile context managers
			and open files without extracting the entire archive'''
		pass
		return None
        
	def detect_files(self):
		test = all([f.isfile() for f in self.json_files])
		return test

    #Utility Functions
	def ask_date(self):
		'''Launch a date picker with pysimplegui'''
		self.months_back = 24
		self.last_time = date.today()
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
	    
	""" def blur_faces(self, img_path):
		'''Detect the faces in an image & apply blur effect over each'''
		img = cv2.imread(img_path)
		faces = face_recognition.face_locations(img)
		logging.debug(f'Blurring {len(faces)} faces for image at location: {img_path}')
		for (top, right, bottom, left) in faces:
			face_image = img[top:bottom, left:right]
			img[top:bottom, left:right] = cv2.GaussianBlur(face_image, (99, 99), 30)
		return img """

	def genCSV(self, csv_name, header, data):
		'''Generate CSV files from data (a list of dicts)'''
		logging.debug(f'Creating the file {csv_name}')
		csv_out = self.outbox_path / csv_name + ".csv"
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
	
	def sys_check(self):
		self.timetype = 1 if platform.system() == 'Windows' else -1
		self.time_string_opts = {
			1: lambda ts: ts.strftime("%#I:%M %p"),
			-1: lambda ts: ts.strftime("%-I:%M %p")
		}
		return True
		
	def time_string(self, timestamp):
		return self.time_string_opts[self.time_type](timestamp)
	
	def parse_img_ext(self, filepath):
		if len(Path(media).suffix) == 0:
			filename, ext_type = media, 'jpg'
		else:
			filename, ext_type = media.split(".")
		if ext_type in self.VALID_TYPES:
			#TODO????
			return False
		
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
		
		date = ts.date()
		time = self.time_string(ts)
		return ts, date, time
#%%	    
@dataclass
class Media():
	fp_src: str
	fp_out: str
	date: str
	time: str
	comment: str
	file_type: str

    #Parse Functions

class FBParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass
        
class IGParser(SMParser):
	def __init__(self, person_name, person_alias, zip_path, home_dir=None):
		pass
        
	def parse_posts(self, parsed_path):
		#--- PHOTOS
		print("Parsing Posts")
		posts_header = ["Date", "Time", "Path", "Caption", "Likes", "Comments"]
		posts_rows = []
		media_timestamps = []
		self.post_counter = 0

		posts_data = self.get_json("content", "posts_1")
		#jposts[0].media[0].uri, .creation_timestamp, .title
		print("Parsing posts")
		valid_posts = [p for p in posts_data if self.in_date_range(p.timestamp)]
		for i, post in enumerate(valid_posts):
			for j, photo in post.media:
				outpath = self.outbox_path / "media" / f'Post{i}' / f'Photo{chr(97+j)}'
				ts, date, time = parse_time(post.creation_timestamp)
				img_ext = self.parse_ext(photo.uri)
				ph = Media(photo.uri, outpath, date, time, photo.title, img_ext)

		post_counter, new_rows = self.parse_type(posts_data, post_counter, months_back, last_date, media_timestamps)
		media_parsed.extend(new_rows)

		#--- STORIES
		stories_data = self.get_json("content", "stories")
		#sposts.ig_stories[0].uri
		#story_list = stories_data["ig_stories"]
		print("Parsing stories")
		post_counter, new_rows = self.parse_type(story_list, post_counter, media_timestamps, True)
		media_parsed.extend(new_rows)

		#--- PROFILE PICS
		profile_pic_data = self.get_json("content", "profile_photos")
		#prof.ig_profile_picture[0].uri
		#profile_pic_list = profile_pic_data["ig_profile_picture"]
		print("parsing profile pic")
		post_counter, new_rows = self.parse_type(profile_pic_list, post_counter, media_timestamps)
		media_parsed.extend(new_rows)

		self.gen_csv("posts", posts_header, media_parsed)
		return None

	#TODO: Refactor This!
	def parse_type(self, post_lst, post_counter, timestamps_for_media_parsed, story=False):
		tracker = {}  # timestamp -> (post_num, num_pics)
		parsed_rows = []
		for i, post in enumerate(post_lst, post_counter):
			print(f"Post {i} of {len(post_lst)}", end="\r")
			timestamp, date, time = get_timestamp(post.get("creation_timestamp"))
			if self.in_date_range(timestamp):
				caption = post.get("title","")
			'''if timestamp in tracker:  #TODO: PJS Add this back later?
				post_num, num_pics = tracker[timestamp]
				if add_media(media["path"], tracker, timestamp, post_num, num_pics + 1, story):
					tracker[timestamp] = (post_num, num_pics + 1)
			else:'''
			post_num = i    #post_counter
			for num_pics, pic in enumerate(post.get("media",[]), 1):
				
				if self.add_media(pic["uri"], tracker, timestamp, post_num, num_pics, story):
					#tracker[timestamp] = (post_num, num_pics)
					parsed_rows.append([date, time, os.path.join("stories" if story else "media", str(post_num)), clean_text(caption), "", ""])
					timestamps_for_media_parsed.append(timestamp)
		return post_counter+len(post_lst), parsed_rows

	def add_media(self, media, tracker, timestamp, post_num, num_pics, story):
	
		media_src = self.zip_root / media
		media_dest = self.outbox_path / "stories" if story else "media" / str(post_num)
		if not media_dest.is_dir(): media_dest.mkdir(parents=True, exist_ok=True)

		img = blur_faces(media_src)
		if img is None: return False
		cv2.imwrite(media_dest / f"{chr(97+num_pics)}.{ext_type}", img)
		tracker[timestamp] = (post_num, num_pics + 1)
		return True

class TTParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass    

class YTParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass    