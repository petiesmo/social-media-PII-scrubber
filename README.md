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

## Installation
- Download Visual Studio
- Install cmake
- Install dlib (for face_recognition)
- Install spacy
- python -m spacy download en_core_web_sm  (dictionary of names)
- install scrubadub_spacy
- spacy.load('en_core_web_sm')