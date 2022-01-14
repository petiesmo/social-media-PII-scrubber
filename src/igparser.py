#Updated Jan 2022 for IG v2 schema
import zipfile
import glob
import os
import scrubadub
#import nltk
import re
import cv2
import sys
import json
import shutil
from datetime import datetime, timezone, timedelta
import platform
import csv
#import instaloader
import face_recognition
from pathlib import Path
import imghdr

# in: None; out: None
def init():
    testdir = Path(r'C:\Users\pjsmole\Documents\GitHub\social-media-PII-scrubber\test-data')
    tempdir = testdir / "inbox/temp"
    outdir = testdir / "outbox"
    if not tempdir.is_dir(): tempdir.mkdir(parents=True)
    if not outdir.is_dir(): outdir.mkdir()
    #if not os.path.isdir(r'.\inbox\temp'): os.mkdir(r'.\inbox\temp')
    #if not os.path.isdir(r'.\outbox'): os.mkdir(r'.\outbox')
    #nltk.download('punkt')
    return testdir, tempdir, outdir

# globals
test_path, temp_path, outbox_path = init()
#temp_path = os.path.join('inbox', 'temp')
#outbox_path = os.path.join('outbox')
#offline = len(sys.argv) == 2 and sys.argv[1] == 'offline'

# in: None; out: None
def unzip():
    print("unzipping")
    zips = Path(test_path/"inbox").glob("*.zip")  #glob.glob("./inbox/*.zip")
    for zip in [z for z in zips]:
        with zipfile.ZipFile(zip, "r") as zip_ref:
            name = zip_ref.filename
            assert(name[-4:] == ".zip")  #name[:8] == "./inbox/" andg
            name = Path(name).name[:-4]  #name[8:-4]
            dest_path = os.path.join(temp_path, name)
            zip_ref.extractall(dest_path)
        if os.path.isdir("{0}/{1}".format(dest_path,name)): # extracted with an extra folder
            shutil.move(dest_path, dest_path+"1")  # rename parent folder
            shutil.move("{0}/{1}".format(dest_path+"1",name), temp_path)  # move up
            shutil.rmtree(dest_path+"1")  # remove parent folder


def ask_date():
    month_match = re.compile(r"^(\d|\d{2})$")
    months_back = input("How many months back? Enter a 1 or 2 digit number, then press enter: ").strip()
    while month_match.match(months_back) is None:
        months_back = input("Please enter a valid 1 or 2 digit number, then press enter: ").strip()

    date_match = re.compile(r"(^\d{4}-([0]\d|1[0-2])-([0-2]\d|3[01])$|^today$)")
    date_string = input("Parse within {0} month(s) of what date? \"today\" or YYYY-MM-DD, then press enter: ".format(months_back)).strip()
    while date_match.match(date_string) is None:
        date_string = input("Please enter in the proper format (\"today\" or YYYY-MM-DD), then press enter: ").strip()
    timestamp = datetime.today()
    if date_string != "today":
        yr_mo_day = [int(x) for x in date_string.split("-")]
        timestamp = datetime(yr_mo_day[0], yr_mo_day[1], yr_mo_day[2])
    if datetime.today() < timestamp:
        print("Error: date entered is in the future. Let's try again.")
        months_back, timestamp = ask_date()
    return int(months_back), timestamp

def out_of_range(curr, months_back, last_date):
    return (last_date-timedelta(days=months_back*30.4375) >= curr or curr > last_date)

def blur_faces(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None
    faces = face_recognition.face_locations(img)
    for (top, right, bottom, left) in faces:
        face_image = img[top:bottom, left:right]
        face_image = cv2.GaussianBlur(face_image, (99, 99), 30)
        img[top:bottom, left:right] = face_image
    return img

def gen_csv(parsed_path, filename, content):
    print("generating csv")
    csv_out = os.path.join(parsed_path, "{0}.csv".format(filename))
    os.makedirs(os.path.dirname(csv_out), exist_ok=True)
    with open(csv_out, "w+", encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL, lineterminator = '\n')
        for entry in content: csv_writer.writerow(entry)

# in: unzip_path for particular account, filename string like "comments"
# out: list of data
def get_json(unzip_path, filename):
    json_path = os.path.join(unzip_path, "{0}.json".format(filename))
    return json.load(open(json_path))

# in: string
# out: timestamp, time, date
def get_timestamp(when):
    try:
        if when == None:
            timestamp = datetime.today()
        elif type(when) == int: 
            timestamp = datetime.fromtimestamp(when)
        elif "+" in when: 
            when = when[:when.index("+")]
            timestamp = datetime.strptime(when, '%Y-%m-%dT%H:%M:%S')
        date = timestamp.date()
        time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
        return timestamp, date, time
    except ValueError:
        print("ValueError: wasn't able to parse timestamp {0}".format(when))
        timestamp = datetime.today()
        date = timestamp.date()
        time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
        return timestamp, date, time

# in: text; out: cleaned text
def clean_text(text):
    text = scrubadub.clean(text)
    return re.sub(r'@\S*', "{{USERNAME}}", text).encode('latin1', 'ignore').decode('utf8', 'ignore')

def parse_profile_metadata(unzip_path):
    print("parsing profile metadata")
    data = get_json(unzip_path, "account_information\\personal_information")
    username = data['profile_user'][0]["string_map_data"].get('Username').get('value')
    # name = data['name'] if 'name' in data else ''
    return username

def parse_comments(unzip_path, parsed_path, months_back, last_date, username):
    print("parsing comments")
    data = get_json(unzip_path, "comments\\post_comments")
    users_comments_on_own_post = [["Date", "Time", "Content"]]
    users_comments_on_other_post = [["Date", "Time", "Content"]]
    #for section in data:
    for comment in data["comments_media_comments"]:
        ts = comment["string_list_data"][0]["timestamp"]
        comment_value = comment["string_list_data"][0]["value"]
        author = comment["title"]
        
        timestamp, date, time = get_timestamp(ts)
        if out_of_range(timestamp, months_back, last_date): continue
        content = clean_text(comment_value)
        if re.compile(r'^\s*$').match(content): continue
        row = [date, time, content]
        #author = comment[2]
        if author == username:
            if users_comments_on_own_post[-1][2] == content: continue
            users_comments_on_own_post.append(row)
        else:
            if users_comments_on_other_post[-1][2] == content: continue
            users_comments_on_other_post.append(row)
    gen_csv(parsed_path, "users_comments_on_own_post", users_comments_on_own_post)
    gen_csv(parsed_path, "users_comments_on_other_post", users_comments_on_other_post)

def parse_follow(unzip_path, parsed_path):
    print("parsing follow")
    data = get_json(unzip_path, "followers_and_following\\followers")
    data2 = get_json(unzip_path, "followers_and_following\\following")
    follow_parsed = [['Followers', 'Followees'],
        [len(data['relationships_followers']), len(data2['relationships_following'])]]
    gen_csv(parsed_path, "follow", follow_parsed)

# out: true if success
def add_media(unzip_path, unzip_name, media, tracker, timestamp, post_num, num_pics, story):
    if len(Path(media).suffix) == 0:
        filename, ext_type = media, 'jpg'
    else:
        filename, ext_type = media.split(".")
    if ext_type in ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tiff', '.tif']:
        return False
    media_src = os.path.join(unzip_path, media)
    media_dest = os.path.join(outbox_path, unzip_name, "stories" if story else "media", str(post_num))
    if not os.path.exists(media_dest): os.makedirs(media_dest, exist_ok=True)
    img = blur_faces(media_src)
    if img is None: return False
    cv2.imwrite(os.path.join(media_dest, "{0}.{1}".format(chr(97+num_pics), ext_type)), img)
    tracker[timestamp] = (post_num, num_pics + 1)
    return True

def parse_type(post_lst, post_counter, months_back, last_date, timestamps_for_media_parsed, unzip_path, unzip_name, story=False):
    tracker = {}  # timestamp -> (post_num, num_pics)
    parsed_rows = []
    for i, post in enumerate(post_lst, post_counter):
        print("Post {0} of {1}".format(i, len(post_lst)), end="\r")
        timestamp, date, time = get_timestamp(post.get("creation_timestamp"))
        if out_of_range(timestamp, months_back, last_date): continue
            
        '''if timestamp in tracker:  #TODO: PJS Add this back later?
            post_num, num_pics = tracker[timestamp]
            if add_media(unzip_path, unzip_name, media["path"], tracker, timestamp, post_num, num_pics + 1, story):
                tracker[timestamp] = (post_num, num_pics + 1)
        else:'''
        post_num = i    #post_counter
        for num_pics, pic in enumerate(post.get("media",[]), 1):
            caption = post.get("title","")
            if add_media(unzip_path, unzip_name, pic["uri"], tracker, timestamp, post_num, num_pics, story):
                #tracker[timestamp] = (post_num, num_pics)
                parsed_rows.append([date, time, os.path.join("stories" if story else "media", str(post_num)), clean_text(caption), "", ""])
                timestamps_for_media_parsed.append(timestamp)
    return post_counter+len(post_lst), parsed_rows

def parse_posts_offline(unzip_path, months_back, last_date, unzip_name):
    print("parsing offline posts")
    media_parsed = [["Date", "Time", "Path", "Caption", "Likes", "Comments"]]
    timestamps_for_media_parsed = []
    post_counter = 0

    posts_data = get_json(unzip_path, "content\\posts_1")
    #if "photos" in data:
    #photo_video = posts_data["photos"]
    #if "videos" in posts_data: photo_video.extend(posts_data["videos"])
    print("parsing photos and videos")
    post_counter, new_rows = parse_type(posts_data, post_counter, months_back, last_date, timestamps_for_media_parsed, unzip_path, unzip_name)
    media_parsed.extend(new_rows)
    #--- STORIES
    stories_data = get_json(unzip_path, "content\\stories")
    story_list = stories_data["ig_stories"]
    #if "stories" in data:
    print("parsing stories")
    post_counter, new_rows = parse_type(story_list, post_counter, months_back, last_date, timestamps_for_media_parsed, unzip_path, unzip_name, True)
    media_parsed.extend(new_rows)
    #--- PROFILE PICS
    profile_pic_data = get_json(unzip_path, "content\\profile_photos")
    profile_pic_list = profile_pic_data["ig_profile_picture"]
    print("parsing profile pic")
    post_counter, new_rows = parse_type(profile_pic_list, post_counter, months_back, last_date, timestamps_for_media_parsed, unzip_path, unzip_name)
    media_parsed.extend(new_rows)
    return media_parsed, timestamps_for_media_parsed

'''def parse_posts_online(media_parsed, timestamps_for_media_parsed, username):
    print("parsing online posts")
    L = instaloader.Instaloader()
    try:
        L.interactive_login(username)
    except Exception as e:
        print("Failed login with username from download: " + type(e).__name__ + ": {}".format(e))
        username = input('Please enter subject\'s Instagram username: ')
        L.interactive_login(username)
    profile = instaloader.Profile.from_username(L.context, username)
    posts = profile.get_posts()
    for post in posts:
        timestamp = post.date_local
        if timestamp not in timestamps_for_media_parsed: continue
        row = media_parsed[timestamps_for_media_parsed.index(timestamp)]
        row[4] = post.likes
        row[5] = "; ".join([clean_text(comment) for comment in post.get_comments()])
        media_parsed[timestamps_for_media_parsed.index(timestamp)] = row
    return media_parsed
'''
def parse_posts(unzip_path, parsed_path, months_back, last_date, username, unzip_name):
    media_parsed, timestamps_for_media_parsed = parse_posts_offline(unzip_path, months_back, last_date, unzip_name)
    #if not offline:
    #    media_parsed = parse_posts_online(media_parsed, timestamps_for_media_parsed, username)
    gen_csv(parsed_path, "posts", media_parsed)

def parse_all_accounts():
    unzip()
    for unzipped in filter(lambda x: not(x.startswith(".")), os.listdir(temp_path)):
        unzip_path = os.path.join(temp_path, unzipped)
        username = parse_profile_metadata(unzip_path)
        print("parsing user {0}".format(username))
        parsed_path = os.path.join(outbox_path, unzipped)
        months_back, last_date = ask_date()
        parse_comments(unzip_path, parsed_path, months_back, last_date, username)
        parse_follow(unzip_path, parsed_path)
        parse_posts(unzip_path, parsed_path, months_back, last_date, username, unzipped)
    print("cleaning up")
    shutil.rmtree(temp_path)

parse_all_accounts()
