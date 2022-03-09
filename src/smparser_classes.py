#%%
#smparser-classes.py

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, date, timedelta
import itertools
import json
import logging
from pathlib import Path
import platform
import re
from types import SimpleNamespace
import zipfile

from dateutil.relativedelta import relativedelta
import dateparser
import face_recognition
import numpy as np
from PIL import Image, ImageFilter
import PySimpleGUI as sg
import scrubadub
import scrubadub_spacy

#%%
class SMParser():
	def __init__(self, person_name, person_alias, zip_path, home_dir=None, months_back=None, last_time=None):
		self.VALID_TYPES = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tiff', '.tif']
		self.person_name = person_name
		self.person_alias = person_alias
		self.zip_file = zipfile.ZipFile(zip_path)
		self.zip_root = zipfile.Path(self.zip_file)
		self.months_back = months_back if months_back is not None else 24
		self.last_time = last_time if last_time is not None else datetime.today()
		self._date_calc()
		self._sys_check()

		self.home_path = Path(home_dir) if home_dir is not None else Path(zip_path).parent.parent
		self.outbox_path = self.home_path / 'outbox'
		self.media_path = self.outbox_path / 'media'
		self.media_path.mkdir(parents=True, exist_ok=True)
		#self.file_mapping = {}  #{fcsv: {fjson: relpath, fnparse:_, header:[,]}, csvfile2:...}
		self.posts_media = list()

	#Utility Functions
	def _sys_check(self):
		self.timetype = 1 if platform.system() == 'Windows' else -1
		self.time_string_format = {
			1: lambda ts: ts.strftime("%#I:%M %p"),
			-1: lambda ts: ts.strftime("%-I:%M %p")
		}
		return True
	
	def _setup_scrubber(self):
		self.scrubber = scrubadub.Scrubber()
		self.scrubber.add_detector(scrubadub_spacy.detectors.SpacyEntityDetector(model='en_core_web_trf'))
		#scrubber.clean("My name is John and my phone number is 505-222-1138")
		supplied_filth_detector = scrubadub.detectors.UserSuppliedFilthDetector( [{'match': 'Maggie', 'filth_type': 'name', 'ignore_case': False},
			 {'match': 'Nail', 'filth_type': 'name', 'ignore_case': False}
			 {'match': self.personname, 'filth_type':'name', 'ignore_case':True}])
		self.scrubber.add_detector(supplied_filth_detector)
		re.sub(r"@\S*","{{USERNAME}}","@Maggie Nail and my phone number is 505-222-1138")

	def _date_calc(self):
		'''Calculate derived dates and time intervals'''
		self.first_time = self.last_time - relativedelta(months=self.months_back)
		self.num_weeks = (self.last_time - self.first_time).days // 7 + 2
		self.week_bins = [self.last_time - relativedelta(days=7*i) for i in range(self.num_weeks)]
		return None
        
	def in_date_range(self, check_date):
		'''Accepts a Datetime object, returning boolean'''
		#TODO accept either date or datetime
		return self.first_time <= check_date <= self.last_time
        
	def get_json(self, folder, filename):
		'''Retrieves json file and returns an object'''
		json_path = self.zip_root / folder / f"{filename}.json"
		return json.loads(json_path.read_text(), object_hook=lambda d:SimpleNamespace(**d))

	def get_txt(self, folder, filename):
		'''Retrieves txt data file and returns an object'''
		txt_path = self.zip_root / folder / f"{filename}.txt"
		_txt_data = txt_path.read_text()
		recs = _txt_data.split('\n\n')
		drecs = [{k:v for k,v in [p.split(': ',1) for p in t.split('\n')]} for t in recs]
		return SimpleNamespace(**drecs)
g
	def parse_img_ext(self, mediafp):
		ext_type = mediafp.suffix if hasattr(mediafp, 'suffix') else '' 
		return ext_type if ext_type in self.VALID_TYPES else None

	def blur_faces(self, img):
		'''Receives and returns a PIL Image object'''
		faces = face_recognition.face_locations(np.array(img))
		face_boxes = [(d,a,b,c) for (a,b,c,d) in faces]
		for face in face_boxes:
			crop_img = img.crop(face)
			# Use GaussianBlur to blur the face. 
			blur_image = crop_img.filter(ImageFilter.GaussianBlur(radius=10))
			img.paste(blur_image, face)
		return img

	def scrub_and_save_media(self, media_list):
		'''Cycle through all Media objects, anonymizing each by blurring faces'''
		#TODO: Add a Progress Meter!
		#TODO: Add a 'problems' list?
		self.problems = []
		for i, photo in enumerate(media_list):
			try:
				zph = self.zip_file.NameToInfo.get(photo.fp_src, None)
				if zph is None: raise ValueError('Could not retrieve photo from zip')
				with self.zip_file.open(zph) as zip_img:
					img_data = Image.open(zip_img)
					blurred_img = self.blur_faces(img_data)
				if blurred_img is None: raise ValueError('Blurred image not successful')
				if not photo.Path.parent.is_dir(): photo.Path.parent.mkdir(parents=True, exist_ok=True)
				blurred_img.save(photo.Path)
			except Exception as e:
				logging.error(f'Issue with {photo.fp_src}. Skipped')
				self.problems.append(photo)
				continue
		logging.info(f'Media scrub complete. {len(media_list)} images processed.')
		return True

	def genCSV(self, csv_name, header, data):
		'''Generate CSV files from data (a list of dicts)'''
		logging.info(f'Creating the file {csv_name}')
		csv_out = self.outbox_path / f'{csv_name}.csv'
		with open(csv_out, "w+", encoding='utf-8', newline='') as csv_file:
			csv_writer = csv.DictWriter(csv_file, fieldnames=header, extrasaction='ignore')
			csv_writer.writeheader()
			for entry in data:
				csv_writer.writerow(entry)
		return None
    
	def clean_text(self, text):
		_text = re.sub(r'@\S*', "{{USERNAME}}", text).encode('latin1', 'ignore').decode('utf8', 'ignore')
		return self.scrubber.clean(_text)

	@staticmethod
	def ph_num(n):
		'''Consistent photo numbering'''
		return f'{n//26}{chr(65+n%26)}'

	def time_string(self, timestamp):
		return self.time_string_format[self.timetype](timestamp)
		
	def parse_time(self, when):
		'''in: a form of date-time
		out: timestamp, time, date'''
		try:
			if when is None:
				ts = datetime.today()
			elif type(when) == int or (type(when) == str and when.isnumeric()): 
				ts = datetime.fromtimestamp(when)
			else:
				when = when.split("+", 1)[0]
				ts = datetime.strptime(when, '%Y-%m-%dT%H:%M:%S')
				#TODO: Change to dateutil.parser.parse
		except ValueError:
			logging.error(f"ValueError: wasn't able to parse timestamp {when}")
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
	Path: Path
	Caption: str = ""
	Likes: str = ""
	Comments: str = ""
	#Future TODO: Make comments a dict, like **kwargs?

#Parse Functions unique to each platform
class FBParser(SMParser):
	'''Social Media Parser class for Facebook data, v2 Schema'''
	#def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        #pass

	def parse_profile_metadata(self):
		logging.info('Parsing FB profile metadata')
		data = self.get_json('profile_information','profile_information')
		self.username = data.profile_v2.name.full_name
		return None

	def parse_friends(self):
		'''Parse FB Friends - Aggregated counts/totals'''
		logging.info(f'Parsing {self.username} FB friends metadata')
		data = self.get_json('friends_and_followers','friends')
		data2 = self.get_json('friends_and_followers','removed_friends')
		friends_header = ['Total Friends', 'Removed Friends']
		payload = [
			{'Total Friends': len(data.friends_v2), 
			'Removed Friends': len(data2.deleted_friends_v2)}]
		self.genCSV("FB_friends", friends_header, payload)
		return None
	
	def parse_reactions(self):
		'''Parse FB Reactions, aggregating totals by Type and Category'''
		logging.info(f'Parsing {self.username} FB reactions metadata')
		data = self.get_json('comments_and_reactions','posts_and_comments')
		categories = ['photo','comment','post','link','album','video','other']
		react_header = ['Type', 'Total']
		react_header.extend(categories)
		reactions = data.reactions_v2
		try:
			#.timestamp;  .title;   .data[0].reaction.reaction;  .data[0].reaction.actor
			#Per Client: Gather counts by type over the range; don't concat titles or agg by week (for now)
			reactions_inrange = [r for r in reactions if self.in_date_range(datetime.fromtimestamp(r.timestamp))]
			f_reaction_date = lambda r: (datetime.fromtimestamp(r.timestamp)).date()
			f_reaction_type = lambda r: r.data[0].reaction.reaction
			def f_extract_category(react, rcat='other'):
				for cat in categories:
					rcat = cat if cat in react else rcat 
				return rcat

			reactions_dicts = [{'Date': f_reaction_date(r), 'Type': f_reaction_type(r), 'Category': f_extract_category(r.title)} 
								for r in reactions_inrange]
			f_type = lambda r: r["Type"]
			reactions_sorted = sorted(reactions_dicts, key=f_type)
			reactions_by_type = itertools.groupby(reactions_sorted, key=f_type)
			reaction_counts = {rtype: dict(Counter([r['Category'] for r in rlist])) for rtype, rlist in reactions_by_type}
			reaction_totals = Counter(r['Type'] for r in reactions_dicts)
			for rtype, rc in reaction_counts.items():
				rc['Type'] = rtype
				rc['Total'] = reaction_totals[rtype]
		except Exception as e:
			print(f'Error parsing FB reaction: {type(e).__name__}: {e}')
		self.genCSV("FB_reactions", react_header, list(reaction_counts.values()))
		return None
	
	def parse_posts(self):
		'''Parsing of Facebook posts; Scrubbing captions & blurring photos'''
		logging.info(f'Parsing {self.username} FB posts metadata')
		posts_header = ['Date', 'Time', 'Location', 'Post', 'Caption', 'Subject Comments', 'Friend Comments']
		data = self.get_json('posts','your_posts_1')
		posts = data
		payload = list()
		for i, post in enumerate(posts):
			try:
				logging.debug(f'Parsing {i} of {len(posts)} FB posts...')
				caption = list()
				ts = post.timestamp
				pts, pdate, ptime = self.parse_time(ts)
				if not self.in_date_range(pts): continue
				if hasattr(post, 'data'):
					if len(post.data) > 0 and hasattr(post.data[0], 'post'):
						caption.append(self.clean_text(post.data[0].post))
				if hasattr(post, 'title'):
					caption.append(self.clean_text(post.title))
				payload.append({'Date': pdate, 'Time': ptime, 
								'Location': 'Profile', 'Post': 'N/A',
								'Caption': '; '.join(caption), 'Friend Comments': '',
								'Subject Comments': ''})
				if not hasattr(post, 'attachments') or len(post.attachments)==0:
					continue
				attachments = post.attachments[0].data
				for j, att in enumerate(attachments):
					if hasattr(att, 'media'):
						content = att.media
						media_fp = att.media.uri
						caption = [att.media.title]

						img_ext = self.parse_img_ext(Path(media_fp))
						if img_ext is None: continue
						out_path = self.media_path / 'FB' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
						ph = Media(media_fp, img_ext, pdate, ptime, out_path)
						self.posts_media.append(ph)
					elif hasattr(att, 'external_context'):
						content = att.external_context
						caption = [f': {content.uri}']
						media_fp = 'External'
						out_path = ''
					else:
						continue
					
					# Friend Comments, Subject Comments
					fc, sc = [], []
					if hasattr(content, 'description'):
						caption.append(self.clean_text(content.description))
					if hasattr(content, 'comments'):
						for comment in att.media.comments:
							if self.username in comment.author:
								sc.append(f'"{self.clean_text(comment.comment)}"')
								self.rem_comments.append(comment.comment)
							else:
								fc.append(f'"{self.clean_text(comment.comment)}"')
					payload.append({'Date': pdate, 'Time': ptime, 
									'Location': media_fp, 'Post': out_path, 
									'Caption': '; '.join(caption), 
									'Friend Comments': '; '.join(fc),
									'Subject Comments': '; '.join(sc)})
			except Exception as e:
				logging.info(f"Error parsing FB profile update post: {type(e).__name__}: {e}")
				continue
		self.genCSV("FB_posts", posts_header, payload)
		return None

	def parse_profile_updates(self):
		'''Parsing of Facebook profile updates; Scrubbing captions & blurring photos'''
		#Future TODO: Can this be consolidated with FB posts?
		logging.info(f'Parsing {self.username} FB profile updates metadata')
		posts_header = ['Date', 'Time', 'Location', 'Post', 'Caption', 'Subject Comments', 'Friend Comments']
		data = self.get_json('profile_information','profile_update_history')
		posts = data.profile_updates_v2
		payload = list()
		for i, post in enumerate(posts):
			try:
				logging.debug(f'Parsing {i} of {len(posts)} FB profile updates...')
				ts = post.timestamp
				pts, pdate, ptime = self.parse_time(ts)
				if not self.in_date_range(pts): continue
				if not hasattr(post, 'title'): continue
				caption = self.clean_text(post.title)
				payload.append({'Date': pdate, 'Time': ptime, 
								'Location': 'Profile', 'Post': 'N/A',
								'Caption': caption, 'Friend Comments': '',
								'Subject Comments': ''})
				if not hasattr(post, 'attachments'): continue
				attachments = post.attachments[0].data
				for j, att in enumerate(attachments):
					if not hasattr(att, 'media'): continue
					content = att.media
					media_fp = att.media.uri
					img_ext = self.parse_img_ext(Path(media_fp))
					if img_ext is None: continue
					#Friend Comments, Subject Comments
					fc, sc = [], []
					if hasattr(content, 'comments'):
						for comment in att.media.comments:
							if self.username in comment.author:
								sc.append(f'"{self.clean_text(comment.comment)}"')
								self.rem_comments.append(comment.comment)
							else:
								fc.append(f'"{self.clean_text(comment.comment)}"')

					out_path = self.media_path / 'FB' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
					ph = Media(media_fp, img_ext, pdate, ptime, out_path)
					self.posts_media.append(ph)
					payload.append({'Date': pdate, 'Time': ptime, 
									'Location': media_fp, 'Post': out_path, 
									'Caption': caption, 
									'Friend Comments': ';'.join(fc),
									'Subject Comments': ';'.join(sc)})
			except Exception as e:
				logging.info(f"Error parsing FB profile update post: {type(e).__name__}: {e}")
				continue
		self.genCSV("FB_profile_updates", posts_header, payload)
		return None

	def parse_comments(self):
		'''Parsing of FB Comments & Likes'''
		logging.info(f'Parsing {self.username} FB comments & likes metadata')
		data = self.get_json('comments_and_reactions','comments')
		comment_header = ['Date', 'Time', 'Author', 'Subject Comments', 'Friend Comments', 'URL']
		comments = data.comments_v2
		payload = []
		for comment in comments:
			try:
				ts = comment.timestamp
				cts, cdate, ctime = self.parse_time(ts)
				if not self.in_date_range(cts): continue
				comment_attachment = comment.attachments
				try:
					cc = comment.data[0].comment.comment
					if cc in self.rem_comments: continue
					comment_text = self.clean_text(cc)
				except:
					comment_text = ''
				payload.append({'Date': cdate, 'Time': ctime,
								'Author': 'Participant', 'Subject Comments': comment_text,
								'Friend Comments': '', 'URL': comment_attachment})
			except Exception as e:
				print(f'Error parsing FB reaction: {type(e).__name__}: {e}')
				continue
		self.genCSV("FB_comments", comment_header, payload)
		return None

	def parse_FB_data(self):
		self.rem_comments = list()
		self.parse_profile_metadata()
		self.parse_friends()
		self.parse_reactions()
		self.parse_posts()
		self.parse_profile_updates()
		#if input(f'Scrub & save {len(self.posts_media)} FB images?') == 'Y':
		print(f'Scrub & save {len(self.posts_media)} FB images')
		self.scrub_and_save_media(self.posts_media)
		return None

class IGParser(SMParser):
	'''Social Media Parser class for Instagram data, v2 Schema'''
	#def __init__(self, person_name, person_alias, zip_path, home_dir=None):
		#pass
    
	def parse_profile_metadata(self):
		logging.info('Parsing IG profile metadata')
		data = self.get_json('account_information','personal_information')
		self.username = data.profile_user[0].string_map_data.Username.value
		return None
	
	def parse_comments(self):
		'''Parsing of IG Comments with scrubbed content'''
		logging.info('Parsing IG comments')
		data = self.get_json('comments', 'post_comments')
		comments_header = ['Date', 'Time', 'Content']
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
		self.genCSV("IG_users_comments_on_own_post", comments_header, users_comments_on_own_post)
		self.genCSV("IG_users_comments_on_other_post", comments_header, users_comments_on_other_post)

	def parse_follow(self):
		'''Parsing followers - Aggregated Total counts'''
		logging.info("Parsing IG Follow")
		data = self.get_json('followers_and_following', 'followers')
		data2 = self.get_json('followers_and_following', 'following')
		follow_header = ['Followers', 'Following']
		payload = [
			{'Followers': len(data.relationships_followers), 
			'Following': len(data2.relationships_following)}]
		self.genCSV("IG_follow", follow_header, payload)

	def parse_posts(self):
		'''Parsing IG Posts - Indexing of Media paths in Posts & Stories'''
		logging.info('Parsing IG posts')
		posts_header = ["Date", "Time", "Path", "Caption", "Likes", "Comments"]
		#--- PHOTOS
		posts_data = self.get_json("content", "posts_1")
		#jposts[0].media[0].uri, .creation_timestamp, .title
		#valid_posts = [p for p in posts_data if self.in_date_range(datetime.fromtimestamp(p.creation_timestamp))]
		for i, post in enumerate(posts_data):
			ts = post.creation_timestamp if hasattr(post, 'creation_timestamp') else None
			comment = post.title if hasattr(post, 'title') else ""
			for j, photo in enumerate(post.media):
				ts = ts if ts is not None else photo.creation_timestamp
				pts, date, time = self.parse_time(ts)
				if not self.in_date_range(pts): continue
				comment += self.clean_text(photo.title)
				img_fp = photo.uri
				img_ext = self.parse_img_ext(Path(img_fp))
				if img_ext is None: continue
				out_path = self.media_path / 'IG' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
				ph = Media(img_fp, img_ext, date, time, out_path, comment)
				self.posts_media.append(ph)

		#--- STORIES
		logging.info("Parsing IG stories")
		stories_data = self.get_json("content", "stories")
		#sposts.ig_stories[0].uri
		valid_stories = [s for s in stories_data.ig_stories if self.in_date_range(datetime.fromtimestamp(s.creation_timestamp))]
		for i, story in enumerate(valid_stories):
			img_fp = story.uri
			ts, date, time = self.parse_time(story.creation_timestamp)
			img_ext = self.parse_img_ext(Path(img_fp))
			if not self.in_date_range(ts) or img_ext is None: continue
			out_path = self.media_path / 'IG' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
			comment = self.clean_text(story.title)
			ph = Media(img_fp, img_ext, date, time, out_path, comment)
			self.posts_media.append(ph)

		#--- PROFILE PICS
		logging.info("Parsing IG profile pic")
		profile_pic_data = self.get_json("content", "profile_photos")
		#prof.ig_profile_picture[0].uri
		for i, photo in enumerate(profile_pic_data.ig_profile_picture):
			img_fp = photo.uri
			img_ext = self.parse_img_ext(Path(img_fp))
			out_path = self.media_path / 'IG' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
			ts, date, time = self.parse_time(photo.creation_timestamp)
			comment = self.clean_text(photo.title)
			ph = Media(img_fp, img_ext, date, time, out_path, comment)
			self.posts_media.append(ph)
		
		#--- Build the csv
		logging.debug(self.posts_media)
		posts_row_data = [r.__dict__ for r in self.posts_media]
		self.genCSV("IG_Posts", posts_header, posts_row_data)
		return None

	def parse_IG_data(self):
		self.parse_profile_metadata()
		self.parse_follow()
		self.parse_comments()
		self.parse_posts()
		#if input(f'Scrub & save {len(self.posts_media)} IG images?') == 'Y':
		print(f'Scrub & save {len(self.posts_media)} IG images')
		self.scrub_and_save_media(self.posts_media)

class TTParser(SMParser):
	'''Parser class for TikTok user data'''
	def __init__(self, person_name, person_alias, zip_path, home_dir=None):
		pass    

class SCParser(SMParser):
	'''Parser class for SnapChat data'''
	def __init__(self, person_name, person_alias, zip_path, home_dir=None):
		pass    
#%%
def main_test():
	#For Testing
	fp_person = Path(r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\inbox\TEMP\Person3')
	person_name = 'MM'
	person_alias = 'Volunteer3'
	months_back = 24
	last_time = datetime.today()

	logfile = fp_person / 'parser.log'
	logging.basicConfig(format='%(asctime)s|%(levelname)s:%(message)s', filename=logfile, level=logging.DEBUG, encoding='utf-8')

	IGzip = fp_person / 'Inbox' / 'IG-Instagram-Meg-Nesi.zip'
	FBzip = fp_person / 'Inbox' / 'FB-facebook-MMaron-100010016043358.zip'

	logging.info(f'Person: {person_name}, Alias: {person_alias}')
	logging.info(f'Last time: {last_time}, Months Back: {months_back}')
	logging.info(f'IG File: {IGzip}')
	logging.info(f'FB File: {FBzip}')

	IG = IGParser(person_name, person_alias, IGzip, home_dir=fp_person, months_back=months_back, last_time=last_time)
	IG.parse_IG_data() 
	print('IG Parsing complete')
	
	FB = FBParser(person_name, person_alias, FBzip, home_dir=fp_person, months_back=months_back, last_time=last_time)
	FB.parse_FB_data()
	print('FB Parsing complete')

	print('al fin')

if __name__ == "__main__":
	main_test()
# %%
