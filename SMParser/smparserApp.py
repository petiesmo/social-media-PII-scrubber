#! /bin/python3 smparserApp.py
#%%
import logging
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
import PySimpleGUI as sg
from .GUI import candidateGUI
from .smparsers import IGParser, FBParser
from .smparsers import TTParser, SCParser
#%%
def main_sm_parsing(TESTMODE=False):
	load_dotenv()
	candidate_info = candidateGUI() if not TESTMODE else fake_GUI_output
	if candidate_info is None: return None 
	ci = SimpleNamespace(**candidate_info) 
	logfile = Path(ci.fp_person) / 'parser.log'
	logging.basicConfig(format='%(asctime)s|%(levelname)s:%(message)s', filename=logfile, level=logging.DEBUG) #, encoding='utf-8')
	#Diagnostics
	logging.info(f'Candidate ID: {ci.person_ID_number}')
	logging.info(f'Person: {ci.person_first_name} {ci.person_last_name}, Aliases: {ci.person_alias}')
	logging.info(f'Last time: {ci.last_date}, Months Back: {ci.months_back}')
	logging.info(f'FB File: {ci.FBzip}\nIG File: {ci.IGzip}\nTT file: {ci.TTzip}\nSC file: {ci.SCzip}')
	#Launch Parsers
	if not ci.FByes or not Path(ci.FBzip).suffix=='.zip':
		logging.info('Skipped FB')
	else:
		sg.popup_timed('FB Parsing started', non_blocking=True)
		FB = FBParser(	candidate_id=ci.person_ID_number, last_name=ci.person_last_name, first_name=ci.person_first_name, person_alias=ci.person_alias,
					zip_path=ci.FBzip, home_dir=ci.fp_person, months_back=ci.months_back, last_date=ci.last_date)
		logging.info(f'{FB}')
		FB.parse_data()
		logging.info('FB Parsing complete'); sg.popup_timed('FB Parsing complete', non_blocking=True)
		
	if not ci.IGyes or not Path(ci.IGzip).suffix=='.zip':
		logging.info('Skipped IG')
	else:
		sg.popup_timed('IG Parsing started', non_blocking=True)
		IG = IGParser(	candidate_id=ci.person_ID_number, last_name=ci.person_last_name, first_name=ci.person_first_name, person_alias=ci.person_alias,
					zip_path=ci.IGzip, home_dir=ci.fp_person, months_back=ci.months_back, last_date=ci.last_date)
		logging.info(f'{IG}')
		IG.parse_data() 
		logging.info('IG Parsing complete'); sg.popup_timed('IG Parsing complete', non_blocking=True)

	if not ci.TTyes or not Path(ci.TTzip).suffix=='.zip':
		logging.info('Skipped TT'); sg.popup_timed('Skipped TT', non_blocking=True)
	else:
		sg.popup_timed('TT Parsing started', non_blocking=True)
		TT = TTParser(	candidate_id=ci.person_ID_number, last_name=ci.person_last_name, first_name=ci.person_first_name, person_alias=ci.person_alias,
						zip_path=ci.TTzip, home_dir=ci.fp_person, months_back=ci.months_back, last_date=ci.last_date)
		logging.info(f'{TT}')
		TT.parse_data()
		logging.info('TT Parsing complete'); sg.popup_timed('TT Parsing complete', non_blocking=True)

	if not ci.SCyes or not Path(ci.SCzip).suffix=='.zip':
		logging.info('Skipped SC'); sg.popup_timed('Skipped SC', non_blocking=True)
	else:
		sg.popup_timed('SC Parsing started', non_blocking=True)
		SC = SCParser(	candidate_id=ci.person_ID_number, last_name=ci.person_last_name, first_name=ci.person_first_name, person_alias=ci.person_alias,
						zip_path=ci.SCzip, home_dir=ci.fp_person, months_back=ci.months_back, last_date=ci.last_date)
		logging.info(f'{SC}')
		SC.parse_data() 
		logging.info('SC Parsing complete'); sg.popup_timed('SC Parsing complete', non_blocking=True)
	return True

	
if __name__ == '__main__':
	#Setup GUI and Logging settings
	tempdir = Path.home() / "AppData" / "Local" / "SMParser"
	if not tempdir.exists(): tempdir.mkdir()
	HISTORY = f"{tempdir / 'history.json'}"
	#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
	
	main_sm_parsing()
	sg.Print('SM Parsing completed.'); logging.info('SM Parsing program complete')
	print('al fin')

#--- Input Data For testing only ---
fake_GUI_output = {
	'person_first_name':	'Maggie',
	'person_last_name':		'Nail',
	'person_alias':			'megs',
	'last_date':			'2022-03-24',
	'months_back':			'24',
	'fp_person':			r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\Good Test\Person11',
	'FByes': True, 'IGyes': True, 'TTyes': True, 'SCyes': False,
	'FBzip':				r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\Good Test\Person1\Inbox\FB-facebook-maggienail16.zip',
	'IGzip':				r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\Good Test\Person1\Inbox\IG-volunteer1-maggie.zip',
	'TTzip':				r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\TikTok\TikTok1.zip',
	'SCzip':				''
}

#us = sg.UserSettings()
#sg.user_settings_filename(path=tempdir)