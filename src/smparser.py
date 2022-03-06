#! /bin/python3/smparser.py

import PySimpleGUI as sg
from pathlib import Path
from datetime import datetime
import logging
import sys

from smparser_classes import SMParser, IGParser, FBParser, Media

def resource_path(relative_path):
	'''Discovers the temporary extract folder for the Executable,
		for loading stored images or other data'''
	try:
		base_path = Path(sys._MEIPASS)
	except Exception:
		base_path = Path.cwd()
	return str(base_path / relative_path)

def parse_main():
	tempdir = Path.home() / "AppData" / "Local" / "SMParser"
	if not tempdir.exists(): tempdir.mkdir()
	us = sg.UserSettings()
	sg.user_settings_filename(path=tempdir)
	#logfile = f"{tempdir / 'smparser.log'}"
	HISTORY = f"{tempdir / 'history.json'}"
	
	sg.theme('DarkBrown4')
	fp_person = Path(sg.popup_get_folder('Select the folder for the Person.\n(Outbox folder will be created here)\n(Typically, Inbox folder is here also)', 
					title='Person Folder', history=True, history_setting_filename=HISTORY, image=LOGO))
	logfile = f"{fp_person / 'parser.log'}"
	logging.basicConfig(format="%(asctime)s|%(levelname)s:%(message)s", filename=logfile, level=logging.DEBUG) # encoding='utf-8')
	
	person_name = sg.popup_get_text('Enter Person name or initials', title="Person's Name", image=LOGO)
	person_alias = sg.popup_get_text('Enter an Alias for person', title="Alias")
	_last_time = sg.popup_get_date(title='Choose Start Date',no_titlebar=False)
	if _last_time is not None:
		m,d,y = _last_time
		last_time = datetime(y,m,d)
	else:
		last_time = datetime.today()
	_months_back = sg.popup_get_text('How many months back?', "Months Back", '24')
	months_back = int(_months_back) if _months_back.isnumeric() and int(_months_back) > 0 else 24

	FBzip = sg.popup_get_file('Select Facebook(FB) zip file', title='FB Zip file', 
								default_path=f"{fp_person / 'Inbox'}", default_extension='.zip', 
								history=True, history_setting_filename=HISTORY)  
	IGzip = sg.popup_get_file('Select Instagram(IG) zip file', title='IG Zip file', 
								default_path=f"{fp_person / 'Inbox'}", default_extension='.zip', 
								history=True, history_setting_filename=HISTORY) 

	logging.info(f'Person: {person_name}, Alias: {person_alias}')
	logging.info(f'Last time: {last_time}, Months Back: {months_back}')
	logging.info(f'FB File: {FBzip}')
	logging.info(f'IG File: {IGzip}')
	
	
	if FBzip is None:
		logging.info('Skipped FB')
	else:
		FB = FBParser(person_name, person_alias, FBzip, home_dir=fp_person, months_back=months_back, last_time=last_time)
		FB.parse_FB_data()
		print('FB Parsing complete')

	if IGzip is None:
		logging.info('Skipped IG')
	else:
		IG = IGParser(person_name, person_alias, IGzip, home_dir=fp_person, months_back=months_back, last_time=last_time)
		IG.parse_IG_data() 
		print('IG Parsing complete')

	print('al fin')

if __name__ == '__main__':
	LOGO = resource_path(r'BrownU_logo.png')
	parse_main()