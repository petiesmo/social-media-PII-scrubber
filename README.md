# social-media-PII-scrubber
Python utility for Parsing and scrubbing PII from social media dumps
*Credit: Derived from jwindha1/sm-parser (which was forked from cspang1 & ndo3)*

## Extending functionality to include:
- Facebook (v2 Schema)
- Instagram (v2 Schema)
- Snapchat
- TikTok

## Codebase improvements:
- Classes to consolidate multi-use functions and data management
- Lower temp memory demands: Zip files are not unzipped/destroyed
- GUI: Simple input form for input values & launch parser

![SMParser Main Screen](https://raw.githubusercontent.com/petiesmo/social-media-PII-scrubber/pjs-dev/SMParser_MainScreen.PNG)

## Installation sequence
- Download Visual Studio
- Install cmake
- Install dlib (for face_recognition)
- Install spacy
- python -m spacy download en_core_web_sm  (dictionary of names)
- install scrubadub_spacy
- modify scrubadub_spacy\detectors\spacy.py to recognize en_core_web_sm as a valid library
-- (edit) Line 66:     "en": "en_core_web_sm",
-- (add)  Line 148:     models.append('en_core_web_sm')
- Note: The Pyinstaller process (from launch_smparser.spec) requires numerous 'hook' files to collect the hidden imports and data files.  These are included in the ./hooks folder.  Several 'standard' hooks were also revised to 'collectall' - [numpy, packaging, sacremoses...] 

## Release Notes
- v0.3 - TTParser modified to suit data anonymity
- v0.2 - SCParser added; New feature: Alias a custom list of values; Fix: Update Starting Date as duration is changed
