#! /bin/python3/smparser.py
#%%
from pathlib import Path
from datetime import datetime
import logging
import sys

import PySimpleGUI as sg
from smparser_classes import IGParser, FBParser
#%%
def resource_path(relative_path):
	'''Discovers the temporary extract folder for the Executable,
		for loading stored images or other data'''
	try:
		base_path = Path(sys._MEIPASS)
	except Exception:
		base_path = Path.cwd()
	return str(base_path / relative_path)

def GUI():
	#def sB (label):
	#	return sg.FileBrowse(button_text=label, target=(sg.ThisRow,-1))
		
	def get_zip_file(sm_platform, home_path):
		return sg.popup_get_file(f'Select {sm_platform} zip file', title='Select Zip file', 
								default_path=f"{home_path / 'Inbox'}", default_extension='.zip', 
								history=True, history_setting_filename=HISTORY)  
	zipfiles = ['ABC123.zip','adeedooda.zip', 'zipperof.zip']
	'''Window for user inputs to launch the scrubber process'''
	layout = [	[sg.Titlebar('PII Scrubber - Candidate Infomation')],
				[sg.T('Fill in details for this Candidate:')],
				[sg.T('First Name: '), sg.I(key='person_first_name') ],
				[sg.T('Last Name: '), sg.I(key='person_last_name')],
				[sg.T('Alias: '), sg.I(key='person_alias')],
				[sg.T('Pick last date'), sg.I(key='last_date'), sg.CalendarButton('<<< End Date')],
				[sg.T('How many months back?')], [sg.Slider(range=(6,120), resolution=6, default_value=24, key='months_back', size=(30,5), orientation='horizontal')],
				[sg.HorizontalSeparator()],
				[sg.T('Choose Main Directory: '), sg.I(key='fp_person'), sg.FolderBrowse('<<< HOME')],
				[	#sg.Column([[sg.Listbox(zipfiles, size=(25,8), key='-ZIPS-')]]),
					sg.Column([	[sg.CB('FB',default=True,enable_events=True, k='FByes')],
								[sg.CB('IG',default=True,enable_events=True, k='IGyes')],
								[sg.CB('TT',default=True,enable_events=True, k='TTyes')],
								[sg.CB('SC',default=True,enable_events=True, k='SCyes')]]),
					sg.Column([	[sg.I(key='FBzip'), sg.FileBrowse('<<< FB')],
								[sg.I(key='IGzip'), sg.FileBrowse('<<< IG')],
								[sg.I(key='TTzip'), sg.FileBrowse('<<< TT')],
								[sg.I(key='SCzip'), sg.FileBrowse('<<< SC')]])
				],
				[sg.T('')],
				[sg.Image(LOGO), sg.OK(), sg.Cancel()],
				[sg.StatusBar('Not all values filled', key='-STATUS-', justification='right')]
			]

	window = sg.Window('Candidate Info', layout=layout, finalize=True)

	# Event Loop
	while True:     
		event, values = window.read()
		if event in (sg.WIN_CLOSED, 'Cancel'):
			logging.info('The User closed the data entry screen')
			break
		if event == 'OK':
			#window['-TEXT-KEY-'].update(values['-INPUT-'])
			break
	window.close()
	return values

def parse_main():
	#Request path for output files
	fp_person = Path(sg.popup_get_folder('Select the folder for the Person.\n(Outbox folder will be created here)\n(Social Media zip files are typically here also)', 
					title='Person Folder', history=True, history_setting_filename=HISTORY, image=LOGO))
	logfile = f"{fp_person / 'parser.log'}"
	logging.basicConfig(format="%(asctime)s|%(levelname)s:%(message)s", filename=logfile, level=logging.DEBUG) # encoding='utf-8')
	#Request parse instance information (IDs, date range)
	person_first_name = sg.popup_get_text("Enter Person's first name", title="Person's First Name", image=LOGO)
	person_last_name = sg.popup_get_text("Enter Person's last name", title="Person's Last Name", image=LOGO)
	person_alias = sg.popup_get_text('Enter an Alias for person', title='Alias')
	_last_date = sg.popup_get_date(title='Choose End Date (Default is Today)', no_titlebar=False)
	if _last_date is not None:
		m,d,y = _last_date
		last_date = datetime(y,m,d)
	else:
		last_date = datetime.today()
	_months_back = sg.popup_get_text('How many months back?', "Months Back", '24')
	months_back = int(_months_back) if (_months_back.isnumeric() and int(_months_back) > 0) else 24
	#Request paths to input data zip files
	FBzip = sg.popup_get_file(	'Select Facebook(FB) zip file', title='FB Zip file', 
								default_path=f"{fp_person / 'Inbox'}", default_extension='.zip', 
								history=True, history_setting_filename=HISTORY)  
	IGzip = sg.popup_get_file(	'Select Instagram(IG) zip file', title='IG Zip file', 
								default_path=f"{fp_person / 'Inbox'}", default_extension='.zip', 
								history=True, history_setting_filename=HISTORY) 
	#Diagnostics
	logging.info(f'Person: {person_first_name} {person_last_name}, Alias: {person_alias}')
	logging.info(f'Last time: {last_date}, Months Back: {months_back}')
	logging.info(f'FB File: {FBzip}')
	logging.info(f'IG File: {IGzip}')
	#Launch Parsers
	if FBzip is None:
		logging.info('Skipped FB')
	else:
		FB = FBParser(	last_name=person_last_name, first_name=person_first_name, person_alias=person_alias,
						zip_path=FBzip, home_dir=fp_person, months_back=months_back, last_date=last_date)
		FB.parse_FB_data()
		logging.info('FB Parsing complete')
		sg.popup_timed('FB Parsing complete', non_blocking=True)

	if IGzip is None:
		logging.info('Skipped IG')
	else:
		IG = IGParser(	last_name=person_last_name, first_name=person_first_name, person_alias=person_alias,
						zip_path=IGzip, home_dir=fp_person, months_back=months_back, last_date=last_date)
		IG.parse_IG_data() 
		logging.info('IG Parsing complete')
		sg.popup_timed('IG Parsing complete', non_blocking=True)
	

if __name__ == '__main__':
	#Setup GUI and Logging settings
	LOGO = resource_path(r'BrownU_logo.png')
	sg.theme('DarkBrown4')
	tempdir = Path.home() / "AppData" / "Local" / "SMParser"
	if not tempdir.exists(): tempdir.mkdir()
	#us = sg.UserSettings()
	#sg.user_settings_filename(path=tempdir)
	HISTORY = f"{tempdir / 'history.json'}"
	GUI()
	#parse_main()
	print('al fin')
