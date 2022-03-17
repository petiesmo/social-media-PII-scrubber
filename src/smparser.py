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
	def get_zip_file(sm_platform, home_path):
		return sg.popup_get_file(f'Select {sm_platform} zip file', title='Select Zip file', 
								default_path=f"{home_path / 'Inbox'}", default_extension='.zip', 
								history=True, history_setting_filename=HISTORY)  
	
	'''Window for user inputs to launch the scrubber process'''
	layout = [	[sg.T('Fill in details for this Candidate:')],
				[sg.T('First Name: '), sg.push(), sg.I(key='person_first_name') ],
				[sg.T('Last Name: '), sg.push(), sg.I(key='person_last_name')],
				[sg.T('Alias: '), sg.push(), sg.I(key='person_alias')],
				[sg.T('Pick last date'), sg.push(), B('End Date>>>'), sg.I(key='last_date', default=None)],
				[sg.T('How many months back?'), sg.Slider(range=(1,120), default_value=24, key='months_back')]
				[sg.HorizontalSeparator()],
				[sg.T('Choose Main Directory: '), sg.push(), sg.B('HOME>>>'), sg.I(key='fp_person') ],
				[	sg.column([[sg.Listbox(zipfiles, size=(25,8), key='-ZIPS-')]]),
					sg.push(),
					sg.column([	[sg.B('FB>>>'), sg.I(key='FBzip', default=None)],
								[sg.B('IG>>>'), sg.I(key='IGzip', default=None)],
								[sg.B('TT>>>'), sg.I(key='TTzip', default=None)],
								[sg.B('SC>>>'), sg.I(key='SCzip', default=None)]], size=35)
				]
				[sg.T('')],
				[sg.Image(LOGO), sg.push(), sg.B('OK'), sg.B('Cancel')],
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
			window['-TEXT-KEY-'].update(values['-INPUT-'])
		if event == 'HOME>>>':
			fp_person = Path(sg.popup_get_folder('Select the folder for the Person.\n(Outbox folder will be created here)\n(Social Media zip files are typically here also)', 
					title='Person Folder', history=True, history_setting_filename=HISTORY, image=LOGO))
			window['fp_person'].update(fp_person)
		if event == 'FB>>>':
			window['FBzip'].update(get_zip_file('Facebook(FB)', fp_person))
		if event == 'IG>>>':
			window['IGzip'].update(get_zip_file('Instagram(IG)', fp_person))
		if event == 'TT>>>':
			window['TTzip'].update(get_zip_file('TikTok(TT)', fp_person))
		if event == 'SC>>>':
			window['SCzip'].update(get_zip_file('Snapchat(SC)', fp_person))
		if event == 'End Date>>>':
			_last_date = sg.popup_get_date(title='Choose End Date (Default is Today)', no_titlebar=False)
			if _last_date is not None:
				m,d,y = _last_date
				last_date = datetime(y,m,d)
			else:
				last_date = datetime.today()
			window['last_date'] = last_date.strftime("%MM-%DD-%YYYY")
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
	logging.info(f'Person: {person_name}, Alias: {person_alias}')
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
	
	parse_main()
	print('al fin')