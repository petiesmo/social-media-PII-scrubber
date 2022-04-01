#! /bin/python3/smparser.py
#%%
from pathlib import Path
from datetime import datetime
from importlib import resources
import logging
from pprint import pprint
import sys
from types import SimpleNamespace

from dateutil.relativedelta import relativedelta
import PySimpleGUI as sg
from smparser_classes import IGParser, FBParser
from smparser_classes2 import TTParser, SCParser
#%%
'''def resource_path(relative_path):
	#Discovers the temporary extract folder for the Executable,
		for loading stored images or other data
	try:
		base_path = Path(sys._MEIPASS)
	except Exception:
		base_path = Path.cwd()
	return str(base_path / relative_path)
'''
def GUI():
	'''Data Entry GUI for one participant record'''
	_TODAY = datetime.today()
	TODAY = (_TODAY.month, _TODAY.day, _TODAY.year)

	'''Window for user inputs to launch the scrubber process'''
	layout = [	[sg.Titlebar('PII Scrubber - Candidate Infomation')],
				[sg.T('Fill in details for this Candidate:')],
				[sg.T('First Name: '), sg.I(key='person_first_name') ],
				[sg.T('Last Name: '), sg.I(key='person_last_name')],
				[sg.T('Alias: '), sg.I(key='person_alias')],
				[sg.T('Pick last date:'), sg.I(key='last_date',size=15), sg.CalendarButton('<<< End Date', format='%m-%d-%Y', default_date_m_d_y=TODAY)],
				[sg.T('How many months back?')], [sg.Slider(range=(6,120), resolution=6, default_value=24, key='months_back', size=(30,5), orientation='horizontal',),
					sg.T('First Date: '), sg.T('', k='first_date')],
				[sg.HorizontalSeparator()],
				[sg.T('Choose Main Directory (Outbox will be created here):')],
				[sg.I(key='fp_person'), sg.FolderBrowse('<<< HOME')],
				[	sg.Column([	[sg.T('Parse?')],
								[sg.CB('FB', default=True, enable_events=True, k='FByes')],
								[sg.CB('IG', default=True, enable_events=True, k='IGyes')],
								[sg.CB('TT', default=True, enable_events=True, k='TTyes')],
								[sg.CB('SC', default=True, enable_events=True, k='SCyes')]]),
					sg.Column([	[sg.T('Zip File Paths:')],
								[sg.I(key='FBzip', justification='right'), sg.FileBrowse('<<< FB')],
								[sg.I(key='IGzip', justification='right'), sg.FileBrowse('<<< IG')],
								[sg.I(key='TTzip', justification='right'), sg.FileBrowse('<<< TT')],
								[sg.I(key='SCzip', justification='right'), sg.FileBrowse('<<< SC')]
								])
				],
				[sg.T('')],
				[sg.Image(LOGO), sg.OK(), sg.Cancel()],
				[sg.StatusBar('Enter Candidate Data', key='-STATUS-', justification='right')]
			]

	window = sg.Window('Candidate Info', layout=layout, finalize=True, margins=20)

	# Event Loop
	while True:     
		event, values = window.read(timeout=1000)
		#window['first_date'].update(datetime(values['<<< End Date']) - relativedelta(months=int(values['months_back'])))
		if event in (sg.WIN_CLOSED, 'Cancel'):
			logging.info('The User closed the data entry screen')
			break
		if event == 'OK':
			#window['-TEXT-KEY-'].update(values['-INPUT-'])
			break
	window.close()
	return values

#--- For testing only ---
fake_GUI_output = {
	'person_first_name':	'Maggie',
	'person_last_name':		'Nail',
	'person_alias':			'megs',
	'last_date':			'2022-03-24',
	'months_back':			'24',
	'fp_person':			r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\Good Test\Person9',
	'FByes': False, 'IGyes': False, 'TTyes': True, 'SCyes': False,
	'FBzip':				r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\Good Test\Person1\Inbox\FB-facebook-maggienail16.zip',
	'IGzip':				r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\Good Test\Person1\Inbox\IG-volunteer1-maggie.zip',
	'TTzip':				r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data\TikTok\TikTok1.zip',
	'SCzip':				''
}

def main_sm_parsing(TESTMODE=False):
	candidate_info = GUI() if not TESTMODE else fake_GUI_output
	ci = SimpleNamespace(**candidate_info)
	logfile = Path(ci.fp_person) / 'parser.log'
	logging.basicConfig(format='%(asctime)s|%(levelname)s:%(message)s', filename=logfile, level=logging.DEBUG, encoding='utf-8')
	#Diagnostics
	logging.info(f'Person: {ci.person_first_name} {ci.person_last_name}, Alias: {ci.person_alias}')
	logging.info(f'Last time: {ci.last_date}, Months Back: {ci.months_back}')
	logging.info(f'FB File: {ci.FBzip}')
	logging.info(f'IG File: {ci.IGzip}')
	#Launch Parsers
	if ci.FByes:
		FB = FBParser(	last_name=ci.person_last_name, first_name=ci.person_first_name, person_alias=ci.person_alias,
						zip_path=ci.FBzip, home_dir=ci.fp_person, months_back=ci.months_back, last_date=ci.last_date)
		logging.info(f'{FB}')
		FB.parse_data()
		logging.info('FB Parsing complete'); sg.popup_timed('FB Parsing complete', non_blocking=True)
	else:
		logging.info('Skipped FB')

	if ci.IGyes:
		IG = IGParser(	last_name=ci.person_last_name, first_name=ci.person_first_name, person_alias=ci.person_alias,
						zip_path=ci.IGzip, home_dir=ci.fp_person, months_back=ci.months_back, last_date=ci.last_date)
		logging.info(f'{IG}')
		IG.parse_data() 
		logging.info('IG Parsing complete'); sg.popup_timed('IG Parsing complete', non_blocking=True)
	else:
		logging.info('Skipped IG')

	if ci.TTyes:
		TT = TTParser(	last_name=ci.person_last_name, first_name=ci.person_first_name, person_alias=ci.person_alias,
						zip_path=ci.TTzip, home_dir=ci.fp_person, months_back=ci.months_back, last_date=ci.last_date)
		logging.info(f'{TT}')
		TT.parse_data()
		logging.info('TT Parsing complete'); sg.popup_timed('TT Parsing complete', non_blocking=True)
	else:
		logging.info('Skipped TT'); sg.popup_timed('Skipped TT', non_blocking=True)

	if ci.SCyes:
		SC = SCParser(	last_name=ci.person_last_name, first_name=ci.person_first_name, person_alias=ci.person_alias,
						zip_path=ci.SCzip, home_dir=ci.fp_person, months_back=ci.months_back, last_date=ci.last_date)
		logging.info(f'{SC}')
		SC.parse_data() 
		logging.info('SC Parsing complete'); sg.popup_timed('SC Parsing complete', non_blocking=True)
	else:
		logging.info('Skipped SC'); sg.popup_timed('Skipped TT', non_blocking=True)

if __name__ == '__main__':
	#Setup GUI and Logging settings
	LOGO = resources.read_bytes('data', 'BrownU_logo.png')
	sg.theme('DarkBrown4')
	#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
	tempdir = Path.home() / "AppData" / "Local" / "SMParser"
	if not tempdir.exists(): tempdir.mkdir()
	HISTORY = f"{tempdir / 'history.json'}"
	
	main_sm_parsing()
	print('al fin')

#us = sg.UserSettings()
#sg.user_settings_filename(path=tempdir)