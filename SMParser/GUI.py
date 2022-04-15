# GUI.py
from datetime import datetime
from importlib import resources
import logging

from dateutil.relativedelta import relativedelta
from dateutil import parser as dt_parser
import PySimpleGUI as sg
from . import appresources

def appGUI():
	print('TODO: Future improvement to launch participant entry without restarting program')
	sg.theme('DarkBrown4')
	return None

def candidateGUI():
	'''Data Entry GUI for one participant record'''
	sg.theme('DarkBrown4')
	_TODAY = datetime.today()
	TODAYmdy = (_TODAY.month, _TODAY.day, _TODAY.year)
	TODAYtxt = datetime.strftime(_TODAY, '%m-%d-%Y')
	THEN = _TODAY - relativedelta(months=24)
	LOGO = resources.read_binary(appresources, 'BrownU_logo.png')
	sg.Print(TODAYtxt)

	'''Window for user inputs to launch the scrubber process'''
	layout = [	[sg.Titlebar('PII Scrubber - Candidate Infomation')],
				[sg.T('Fill in details for this Candidate:')],
				[sg.Column([[sg.T('First Name: ')],
							[sg.T('Last Name: ')],
							[sg.T('Alias List: \n(Separate by commas)')]]),
				sg.Column([	[sg.I(key='person_first_name') ],
							[sg.I(key='person_last_name')],
							[sg.I(key='person_alias')]])
				],
				[sg.T('Pick last date:'), sg.I(key='last_date',size=15, default_text=TODAYtxt), sg.CalendarButton('<<< End Date', format='%m-%d-%Y', default_date_m_d_y=TODAYmdy)],
				[sg.T('How many months back?')], 
				[sg.Slider(range=(6,120), resolution=6, default_value=24, key='months_back', size=(25,5), orientation='horizontal'), sg.T('First Date: '), sg.T(THEN, k='first_date')],
				[sg.HorizontalSeparator()],
				[sg.T('Choose Main Directory'),sg.T('(Outbox will be created here):')],
				[sg.I(key='fp_person'), sg.FolderBrowse('<<< HOME')],
				[sg.Column([[sg.T('Parse?')],
							[sg.CB('FB', default=True, enable_events=True, k='FByes')],
							[sg.CB('IG', default=True, enable_events=True, k='IGyes')],
							[sg.CB('TT', default=True, enable_events=True, k='TTyes')],
							[sg.CB('SC', default=True, enable_events=True, k='SCyes')]]),
				sg.Column([	[sg.T('Zip File Paths:')],
							[sg.I(key='FBzip', justification='right'), sg.FileBrowse('<<< FB',size=7)],
							[sg.I(key='IGzip', justification='right'), sg.FileBrowse('<<< IG',size=7)],
							[sg.I(key='TTzip', justification='right'), sg.FileBrowse('<<< TT',size=7)],
							[sg.I(key='SCzip', justification='right'), sg.FileBrowse('<<< SC',size=7)]])
				],
				[sg.HorizontalSeparator()],
				[sg.Image(LOGO), sg.OK(disabled=True), sg.Cancel()],
				[sg.StatusBar('Enter Candidate Data', key='-STATUS-', justification='right')]
			]

	window = sg.Window('Candidate Info', layout=layout, finalize=True, margins=20)

	# Event Loop
	while True:     
		event, values = window.read(timeout=1000)

		THEN = dt_parser.parse(values['last_date']) - relativedelta(months=int(values['months_back']))
		window['first_date'].update(THEN.strftime(format='%m-%d-%Y'))

		OKcond = all([values['last_date'], values['months_back'], values['fp_person'],
					values['FBzip'] if values['FByes'] else True, values['IGzip'] if values['IGyes'] else True,
					values['TTzip'] if values['TTyes'] else True, values['SCzip'] if values['SCyes'] else True])

		if OKcond:
			window['-STATUS-'].update(value='Minimum values defined to Launch Parser')
			window['OK'].update(disabled=False)
		else:
			window['-STATUS-'].update(value='Minimum values NOT defined')
			window['OK'].update(disabled=True)
		
		if event == 'OK':
			break

		if event in (sg.WIN_CLOSED, 'Cancel'):
			logging.info('The User closed the data entry screen')
			window.close()
			return None
	
	window.close()
	return values