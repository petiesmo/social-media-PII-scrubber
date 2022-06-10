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
- Progress bars for longer running processes & Options to skip media (face blurring) sequence

![SMParser Main Screen](https://raw.githubusercontent.com/petiesmo/social-media-PII-scrubber/pjs-dev/SMParser_MainScreen.PNG)

## Installation sequence (for Windows)
- Download Visual Studio
- Install cmake
- Install dlib (for face_recognition)
- python -m textblob.download_corpora (this will download ntlk_data, probably to your home/AppData/roaming folder)
- Relocate nltk_data into your virtual environment .venv folder (path should be ./.venv/nltk_data)
- Note: The Pyinstaller process (from launch_smparser.spec) requires numerous 'hook' files to collect the hidden imports and data files.  These are included in the ./hooks folder.

## Release Notes
- v0.4 - Changed name detector/library to textblob
- v0.3 - TTParser modified to suit data anonymity
- v0.2 - SCParser added; New feature: Alias a custom list of values; Fix: Update Starting Date as duration is changed
