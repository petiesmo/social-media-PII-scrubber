# GUI.py
from datetime import datetime
from importlib import resources
import logging

import PySimpleGUI as sg
from . import appresources

def appGUI():
	print('TODO: Future improvement to launch without restarting program')
	sg.theme('DarkBrown4')
	return None

def candidateGUI():
	'''Data Entry GUI for one participant record'''
	sg.theme('DarkBrown4')
	_TODAY = datetime.today()
	TODAY = (_TODAY.month, _TODAY.day, _TODAY.year)
	LOGO = resources.read_binary(appresources, 'BrownU_logo.png')

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
								[sg.CB('SC', default=False, enable_events=True, k='SCyes')]]),
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
		#TODO: FIX: window['first_date'].update(datetime(values['<<< End Date']) - relativedelta(months=int(values['months_back'])))
		if event in (sg.WIN_CLOSED, 'Cancel'):
			logging.info('The User closed the data entry screen')
			break
		if event == 'OK':
			break
	window.close()
	return values