#smparser-class

import csv
from datetime import datetime, date, timedelta
import json
import logging
from pathlib import Path
from types import SimpleNamespace
import zipfile

import cv2
import face_recognition

def gist_json_object():
    data = '{"name":"John Smith","Hometown":{"name":"New York","id":123}}'
    x = json.loads(data, object_hook=lambda d:SimpleNamespace(**d))
    print(x.name, x.hometown.name, x.hometown.id)
    return x

class SMParser():
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        self.SUPPORTED_TYPES = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tiff', '.tif']
        self.zip_path = Path(zip_path)
        self.person_name = person_name
        self.person_alias = person_alias    #TODO: Ask Jackie if need to create UUID? Answer: No, just allow for User to Input
		self.ask_date()
		
        self.home_path = home_dir if home_dir is None else self.zip_path.parent
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
        self.first_time = self.last_time - timedelta(months=self.months_back)
        return None
        
    def in_date_range(self, check_date):
        '''Accepts a Date object, returning boolean'''
        return self.first_time <= check_date <= self.last_time
        
    def get_json(self, folder, filename):
	    '''Retrieves json file and returns an object'''
	    json_path = self.zip_path / folder / f"{filename}.json"
	    return json.load(open(json_path), object_hook=lambda d:SimpleNamespace(**d))
    
    def blur_faces(self, img_path):
        '''Detect the faces in an image & apply blur effect over each'''
        img = cv2.imread(img_path)
        faces = face_recognition.face_locations(img)
        logging.debug(f'Blurring {len(faces)} faces for image at location: {img_path}')
        for (top, right, bottom, left) in faces:
            face_image = img[top:bottom, left:right]
            img[top:bottom, left:right] = cv2.GaussianBlur(face_image, (99, 99), 30)
        return img

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
    
    def clean_text(text):
	    text = scrubadub.clean(text)
	    return re.sub(r'@\S*', "{{USERNAME}}", text).encode('latin1', 'ignore').decode('utf8', 'ignore')

    #Parse Functions

class FBParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass
        
class IGParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass    

class TTParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass    

class YTParser(SMParser):
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass    