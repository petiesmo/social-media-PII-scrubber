#smparser-classes.py
#%%
import csv
from dataclasses import dataclass
from datetime import datetime
from importlib import resources #.read_binary .read_text
import json
import logging
from pathlib import Path
import platform
import re
from types import SimpleNamespace
import zipfile

import dateutil
from dateutil.relativedelta import relativedelta
import face_recognition
import numpy as np
from PIL import Image, ImageFilter
import PySimpleGUI as sg
import scrubadub
import scrubadub_spacy
#import spacy
#import en_core_web_sm
#nlp = en_core_web_sm.load()


#%%
class SMParserBase():
	VALID_TYPES = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tiff', '.tif']

	def __init__(self, last_name='Doe', first_name='J', person_alias='', zip_path=None, home_dir=None, months_back=None, last_date=None):
		self.last_name = last_name
		self.first_name = first_name
		self.person_alias = person_alias
		self.username = 'default'
		self.zip_file = zipfile.ZipFile(zip_path)
		self.zip_root = zipfile.Path(self.zip_file)

		self.home_path = Path(home_dir) if home_dir is not None else Path(zip_path).parent.parent
		self.outbox_path = self.home_path / 'outbox'
		self.media_path = self.outbox_path / 'media'
		self.media_path.mkdir(parents=True, exist_ok=True)
		self.posts_media = list()

		self.months_back = int(months_back) if months_back is not None else 24
		self.last_date = dateutil.parser.parse(last_date) if last_date is not None else datetime.today()
		self._date_calc()
		self._sys_check()
		self._setup_scrubber()

	def __repr__(self):
		return f'SMParserBase({(f"{k}={v}" for k,v in self.__dict__)})'

	@classmethod
	def from_dict(cls, dict):
		obj = cls()
		obj.__dict__.update(dict)
		return obj

	@property
	def person_name(self):
		return f'{self.first_name} {self.last_name}'

	#Utility Functions
	@classmethod
	def _sys_check(cls):
		cls.timetype = 1 if platform.system() == 'Windows' else -1
		cls.time_string_format = {
			1: lambda ts: ts.strftime("%#I:%M %p"),
			-1: lambda ts: ts.strftime("%-I:%M %p")
		}
		return True
	
	@classmethod
	def _setup_scrubber(cls):
		cls._scrubber = scrubadub.Scrubber()
		cls._scrubber.add_detector(scrubadub_spacy.detectors.SpacyEntityDetector(model='en_core_web_sm'))
		cls._scrubber.add_detector(scrubadub.detectors.DateOfBirthDetector(require_context=False))
		
	def scrubber_update(self):
		custom_detector = scrubadub.detectors.UserSuppliedFilthDetector( [
			{'match': self.last_name, 'filth_type': 'name', 'ignore_case': True},
			{'match': self.first_name, 'filth_type': 'name', 'ignore_case': True},
			{'match': self.username, 'filth_type':'name', 'ignore_case':True}])
		self._scrubber.add_detector(custom_detector)
		logging.debug(self._scrubber.__dict__)
		return self._scrubber

	@property
	def scrubber(self):
		return self._scrubber

	def _date_calc(self):
		'''Calculate derived dates and time intervals'''
		self.first_date = self.last_date - relativedelta(months=self.months_back)
		self.num_weeks = (self.last_date - self.first_date).days // 7 + 2
		self.week_bins = [self.last_date - relativedelta(days=7*i) for i in range(self.num_weeks)]
		return None
        
	def in_date_range(self, check_dt):
		'''	Evaluates whether date falls within the date range specified by the instance
			Input: Datetime object, Output: boolean'''
		#TODO ? accept either date or datetime
		return self.first_date <= check_dt <= self.last_date
        
	def get_json(self, folder, filename):
		'''Retrieves json file and returns an Object'''
		json_path = self.zip_root / folder / f'{filename}.json'
		return json.loads(json_path.read_text(), object_hook=lambda d:SimpleNamespace(**d))

	def get_txt(self, folder, filename):
		'''Retrieves txt data file and returns a List[Dict]'''
		txt_path = self.zip_root / folder / f'{filename}.txt'
		_txt_data = txt_path.read_text(encoding="utf-8")
		recs = _txt_data.split('\n\n')
		drecs = [{k:v for k,v in [p.split(': ',1) for p in t.split('\n')]} for t in recs if len(t)>2]
		return drecs	#SimpleNamespace(**drecs)

	def parse_img_ext(self, mediafp):
		ext_type = mediafp.suffix if hasattr(mediafp, 'suffix') else '' 
		return ext_type if ext_type in self.VALID_TYPES else None

	def blur_faces(self, img):
		''' Input: PIL Image object, 
			Output: PIL Image object (blurred)'''
		faces = face_recognition.face_locations(np.array(img))
		face_boxes = [(d,a,b,c) for (a,b,c,d) in faces]
		for face in face_boxes:
			crop_img = img.crop(face)
			# Use GaussianBlur to blur the face. 
			blur_image = crop_img.filter(ImageFilter.GaussianBlur(radius=10))
			img.paste(blur_image, face)
		return img

	def scrub_and_save_media(self, media_list):
		'''Cycles through a List[Media] objects, anonymizing each by blurring faces'''
		self.problems = []
		MAX = len(media_list)
		for i, photo in enumerate(media_list):
			#Progress Meter
			if not sg.one_line_progress_meter('Media Anonymizer', i+1, MAX, 'Blurring Faces in Media', f'{photo.ImgPath.name}') and i+1 != MAX:
				sg.popup_auto_close('Cancelling your loop...')
				break
			try:
				#Open img file from zip, process, and save out
				zph = self.zip_file.NameToInfo.get(photo.fp_src, None)
				if zph is None: raise ValueError('Could not retrieve photo from zip')
				with self.zip_file.open(zph) as zip_img:
					img_data = Image.open(zip_img)
					blurred_img = self.blur_faces(img_data)
				if blurred_img is None: raise ValueError('Blurred image not successful')
				if not photo.ImgPath.parent.is_dir(): photo.ImgPath.parent.mkdir(parents=True, exist_ok=True)
				blurred_img.save(photo.ImgPath)
			except Exception as e:
				logging.error(f'Issue with {photo.fp_src}. Skipped')
				self.problems.append(photo)
				continue
		logging.info(f'Media scrub complete. {MAX} images processed.')
		logging.info(f'Issues processing {len(self.problems)} photos')
		logging.debug(f'{self.problems}')
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
    
	def clean_text(self, text:str):
		'''Scrub PII from text string'''
		_text = self.scrubber.clean(text)
		return re.sub(r'@\S*', "{{USERNAME}}", _text).encode('latin1', 'ignore').decode('utf8', 'ignore')

	@staticmethod
	def ph_num(n:int):
		'''Returns a sequential photo numbering (0A, 0B, 0C...)'''
		return f'{n//26}{chr(65+n%26)}'

	def time_string(self, timestring:str):
		'''Massages the string representation of time to match the system'''
		return self.time_string_format[self.timetype](timestring)
		
	def parse_time(self, when):
		'''	Input: a form of date-time
			Output: datetime obj, date obj, time string'''
		try:
			if when is None:
				dt = datetime.today()
			elif type(when) == int or (type(when) == str and when.isnumeric()): 
				dt = datetime.fromtimestamp(when)
			else:
				when = when.split("+", 1)[0]
				#ts = datetime.strptime(when, '%Y-%m-%dT%H:%M:%S')
				dt = dateutil.parser.parse(when)
		except ValueError:
			logging.error(f"ValueError: wasn't able to parse timestamp {when}")
			dt = datetime.today()
		finally:
			date = dt.date()
			time = self.time_string(dt)
		return dt, date, time


#%%	    
@dataclass
class Media():
	fp_src: str
	file_type: str
	Date: str
	Time: str
	ImgPath: Path
	Caption: str = ""
	#Likes: str = ""	#Likes & Comments removed per Client guidance
	#Comments: str = ""




#%%
def main_test():
	#For Testing Only
	#fp_person = Path(r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\inbox\TEMP\Person3')
	'''person_name = 'MM'
	person_alias = 'Volunteer3'
	months_back = 24
	last_date = datetime.today()

	logfile = fp_person / 'parser.log'
	logging.basicConfig(format='%(asctime)s|%(levelname)s:%(message)s', filename=logfile, level=logging.DEBUG, encoding='utf-8')

	IGzip = fp_person / 'Inbox' / 'IG-Instagram-Meg-Nesi.zip'
	FBzip = fp_person / 'Inbox' / 'FB-facebook-MMaron-100010016043358.zip'

	logging.info(f'Person: {person_name}, Alias: {person_alias}')
	logging.info(f'Last time: {last_date}, Months Back: {months_back}')
	logging.info(f'IG File: {IGzip}')
	logging.info(f'FB File: {FBzip}')

	IG = IGParser(person_name, person_alias, IGzip, home_dir=fp_person, months_back=months_back, last_date=last_date)
	IG.parse_IG_data() 
	print('IG Parsing complete')
	
	FB = FBParser(person_name, person_alias, FBzip, home_dir=fp_person, months_back=months_back, last_date=last_date)
	FB.parse_FB_data()
	print('FB Parsing complete')'''

	print('al fin')

if __name__ == "__main__":
	main_test()
# %%
