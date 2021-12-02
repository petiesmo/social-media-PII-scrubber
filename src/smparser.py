import zipfile
import glob
import os
import os.path
import contextlib
import re
import sys
import json
import platform
import csv
import scrubadub
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import face_recognition
import cv2
import shutil
import pathlib
import instaloader
from itertools import dropwhile, takewhile
from operator import itemgetter
import re
import nltk
nltk.download("punkt")

if not os.path.isdir('./inbox/temp'): os.mkdir('./inbox/temp')
if not os.path.isdir('./outbox'): os.mkdir('./outbox')
temp_out = os.path.join('inbox', 'temp')
outbox_path = os.path.join('outbox')

rem_comments = []
supported_types = ['.bmp', '.jpeg', '.jpg', '.jpe', '.png', '.tiff', '.tif']
offline = len(sys.argv) == 2 and sys.argv[1] == 'offline'

def blur_faces(image_path):
    print("Blurring faces for image at location: {0}\n".format(image_path))
    img = cv2.imread(image_path)
    faces = face_recognition.face_locations(img)
    for (top, right, bottom, left) in faces:
        face_image = img[top:bottom, left:right]
        face_image = cv2.GaussianBlur(face_image, (99, 99), 30)
        img[top:bottom, left:right] = face_image
    return img

def genCSV(folder, filename, content):
    # Generate CSVs from data
    print('\tDownloading the file {0}...\n'.format(filename, folder))
    csv_out = os.path.join(outbox_path, folder, filename)
    os.makedirs(os.path.dirname(csv_out), exist_ok=True)
    with open(csv_out, "w+", encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL, lineterminator = '\n')
        for entry in content:
            csv_writer.writerow(entry)

def unzip(platform, temp_path):
    print('Unzipping {0} data dumps...'.format(platform), flush=True)
    zips = glob.glob('./inbox/*.zip'.format(platform))
    for i, z in enumerate(zips):
        print('Unzipping {0} of {1} archives...'.format(i+1, len(zips)), flush=True)
        with zipfile.ZipFile(z, "r") as zip_ref:
            name = zip_ref.filename
            assert(name[:8] == "./inbox/" and name[-4:] == ".zip")
            name = name[8:-4]
            path = "./inbox/temp/{0}".format(name)
            zip_ref.extractall(path)
        if os.path.isdir("{0}/{1}".format(path,name)):
            # extracted with an extra folder
            shutil.move(path, path+"1")  # rename parent folder
            shutil.move("{0}/{1}".format(path+"1",name), "./inbox/temp")  # move up
            shutil.rmtree(path+"1")  # remove parent folder
    # ID extracted dataset
    unzips = os.listdir(temp_path)
    ig_regex = re.compile(r'.*_{0}$'.format(platform))
    unzips = list(filter(ig_regex.search, unzips))
    print('\nUnzipping complete!', flush=True)
    return unzips

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

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= BEGIN =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= FACEBOOK =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

# Parse extracted Facebook datasets
for fbu in unzip('facebook', temp_out):
    # Get display name
    profile_path = os.path.join(temp_out, fbu, 'profile_information', 'profile_information.json')
    display_name = fbu

    if os.path.isfile(profile_path):
        profile_json = open(profile_path).read()
        display_name = json.loads(profile_json)['profile']['name']['full_name']

    print('Parsing {0}\'s Facebook...'.format(display_name), flush=True)
    months_back, last_date = ask_date()

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= FB FRIENDS =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    print('Parsing {0}\'s friends...'.format(display_name), flush=True)
    # Parse friends
    friends_parsed = [['Total Friends', 'Removed Friends']]
    friends_path = os.path.join(temp_out, fbu, 'friends', 'friends.json')
    removed_path = os.path.join(temp_out, fbu, 'friends', 'removed_friends.json')
    if os.path.isfile(friends_path):
        friends_json = open(friends_path).read()
        num_friends = len(json.loads(friends_json)['friends'])
        if os.path.isfile(removed_path):
            removed_json = open(removed_path).read()
            removed_friends = json.loads(removed_json)['deleted_friends']
            num_enemies = 0
            for enemy in removed_friends:
                num_enemies += 1
            friends_parsed.append([num_friends, num_enemies])
        else:
            friends_parsed.append([num_friends, 0])

    genCSV(fbu, 'friends.csv', friends_parsed)

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-= FB REACTIONS =-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    # Parse reactions
    print('Parsing {0}\'s reactions...'.format(display_name), flush=True)
    reactions_path = os.path.join(temp_out, fbu, 'likes_and_reactions', 'posts_and_comments.json')
    categories = ['photo', 'comment', 'post', 'link', 'album', 'video', 'other']
    reactions_parsed = [['From', 'To'] + categories]
    if os.path.isfile(reactions_path):
        reactions_json = open(reactions_path).read()
        reactions = json.loads(reactions_json)['reactions']
        react_totals = defaultdict(lambda: defaultdict(int))
        start_date = end_date = False
        for reaction in reactions:
            try:
                timestamp = datetime.fromtimestamp(reaction['timestamp'])
                if out_of_range(timestamp, months_back, last_date): continue
                # Extract reaction details
                if not start_date or not end_date:
                    start_date = end_date = timestamp
                if(abs((start_date - timestamp).days) > 7):
                    tmp_week = []
                    for cat in categories:
                        tmp_cat = ''
                        for react in react_totals[cat]:
                            tmp_cat += react + ': ' + str(react_totals[cat][react]) + ' '
                        tmp_week.append(tmp_cat)
                    reactions_parsed.append([end_date.date(), start_date.date()] + tmp_week)
                    start_date = end_date = timestamp
                    react_totals = defaultdict(lambda: defaultdict(int))
                else:
                    end_date = timestamp

                category = next((cat for cat in categories if cat in reaction['title']), 'other')
                react_totals[category][reaction['data'][0]['reaction']['reaction']] += 1
            except Exception as e:
                print("Error parsing FB reaction: " + type(e).__name__ + ": {}".format(e))
                continue

    genCSV(fbu, 'reactions.csv', reactions_parsed)

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= FB POSTS =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    # Parse posts
    print('Parsing {0}\'s posts...'.format(display_name), flush=True)
    posts_parsed = [['Date', 'Time', 'Location', 'Post', 'Caption', 'Friend Comments', 'Subject Comments']]
    media_root = os.path.join(outbox_path, fbu, 'media')
    pathlib.Path(media_root).mkdir(parents=True, exist_ok=True)
    posts_path = os.path.join(temp_out, fbu, 'posts', 'your_posts_1.json')
    media_id = 0
    if os.path.isfile(posts_path):
        posts_json = open(posts_path).read()
        posts = json.loads(posts_json)
        location = 'Profile'
        post_counter = 1
        rem_comments = []
        for post in posts:
            try:
                print('Parsing {0} of {1} posts...'.format(post_counter, len(posts)), flush=True)
                post_counter += 1
                # Extract comment details
                timestamp = datetime.fromtimestamp(post['timestamp'])
                if out_of_range(timestamp, months_back, last_date): continue
                post_date = timestamp.date()
                post_time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
                if 'data' in post:
                    if len(post['data']) > 0 and 'post' in post['data'][0]:
                        caption = scrubadub.clean(post['data'][0]['post'])
                elif 'title' in post:
                    caption = scrubadub.clean(post['title'])

                if 'attachments' in post:
                    if len(post['attachments']) == 0:
                        continue
                    attachments = post['attachments'][0]['data']
                    for attachment in attachments:
                        if 'media' in attachment:
                            content = attachment['media']
                            media = content['uri']
                        elif 'external_context' in attachment:
                            content = attachment['external_context']
                            caption += ': ' + content['url']
                            media = ''
                        if 'description' in content:
                                caption = scrubadub.clean(content['description'])
                        friend_comments = ''
                        subject_comments = ''
                        if 'comments' in content:
                            for comment in content['comments']:
                                if (display_name in comment['author']):
                                    subject_comments += '"' + scrubadub.clean(comment['comment']) + '", '
                                    rem_comments.append(comment['comment'])
                                else:
                                    friend_comments += '"' + scrubadub.clean(comment['comment']) + '", '
                        scrubadub.clean(caption)
                        media_src = os.path.join(temp_out, fbu, media)
                        filename, file_extension = os.path.splitext(media)
                        media_dest = 'N/A'
                        if file_extension in supported_types:
                            media_id += 1
                            media_dest = os.path.join(media_root, '{0}{1}'.format(media_id, file_extension))
                            cv2.imwrite(media_dest, blur_faces(media_src))
                        entry = [post_date, post_time, location, media_dest, caption.encode('latin1').decode('utf8'), friend_comments.encode('latin1').decode('utf8'), subject_comments.encode('latin1').decode('utf8')]
                        posts_parsed.append(entry)
            except Exception as e:
                print("Error parsing FB post: " + type(e).__name__ + ": {}".format(e))
                continue

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-= FB GROUP POSTS =-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    # Parse group posts
    # print('Parsing {0}\'s group posts...'.format(display_name), flush=True)
    # posts_path = os.path.join(temp_out, fbu, 'groups', 'your_group_membership_activity.json')
    # if os.path.isfile(posts_path):
    #     found_posts += 1
    #     posts_json = open(posts_path).read()
    #     print(json.loads(posts_json))
    #     posts = json.loads(posts_json)['group_posts']
    #     if 'activity_log_data' in posts:
    #         posts = posts['activity_log_data']
    #     post_counter = 1
    #     rem_comments = []
    #     for post in posts:
    #         print('Parsing {0} of {1} group posts...'.format(post_counter, len(posts)), flush=True)
    #         post_counter += 1
    #         # Extract comment details
    #         if datetime.fromtimestamp(post['timestamp']) < datetime.fromisoformat(date_string):
    #             continue
    #         timestamp = datetime.fromtimestamp(post['timestamp'], timezone.utc)
    #         post_date = timestamp.date()
    #         post_time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
    #         subject_comments = ''
    #         location = 'Group'
    #         caption = ''
    #         media_dest = 'N/A'
    #         if 'data' in post:
    #             if 'post' in post['data'][0]:
    #                 caption = scrubadub.clean(post['data'][0]['post'])
    #             else:
    #                 caption = scrubadub.clean(post['title'])
    #             if 'comment' in post['data'][0]:
    #                 subject_comments += '"' + scrubadub.clean(post['data'][0]['comment']['comment']) + '", '
    #                 location = post['data'][0]['comment']['group']
    #             elif 'title' in post:
    #                 location = post['title'].split(' in ',1)[1]
    #         else:
    #             continue
    #         if 'attachments' not in post:
    #             entry = [post_date, post_time, location, media_dest, caption, '', subject_comments]
    #             posts_parsed.append(entry)
    #         else:
    #             attachments = post['attachments'][0]['data']
    #             for attachment in attachments:
    #                 if 'media' in attachment:
    #                     content = attachment['media']
    #                     media = content['uri']
    #                 elif 'external_context' in attachment:
    #                     content = attachment['external_context']
    #                     caption += ': ' + content['url']
    #                     media = ''
    #                 if 'description' in content:
    #                         caption = scrubadub.clean(content['description'])
    #                 friend_comments = ''
    #                 subject_comments = ''
    #                 if 'comments' in content:
    #                     for comment in content['comments']:
    #                         if (display_name in comment['author']):
    #                             subject_comments += '"' + scrubadub.clean(comment['comment']) + '", '
    #                             rem_comments.append(comment['comment'])
    #                         else:
    #                             friend_comments += '"' + scrubadub.clean(comment['comment']) + '", '
    #                 scrubadub.clean(caption)
    #                 media_src = os.path.join(temp_out, fbu, media)
    #                 filename, file_extension = os.path.splitext(media)
    #                 if file_extension in supported_types:
    #                     media_id += 1
    #                     media_dest = os.path.join(media_root, '{0}{1}'.format(media_id, file_extension))
    #                     cv2.imwrite(media_dest, blur_faces(media_src))
    #                 entry = [post_date, post_time, location, media_dest, caption.encode('latin1').decode('utf8'), friend_comments.encode('latin1').decode('utf8'), subject_comments.encode('latin1').decode('utf8')]
    #                 posts_parsed.append(entry)

# =-=-=-=-=-=-=-=-=-=-=-=-=-= FB PROFILE UPDATES =-=-=-=-=-=-=-=-=-=-=-=-=-= #

    # Parse profile update posts
    print('Parsing {0}\'s profile updates...'.format(display_name), flush=True)
    posts_path = os.path.join(temp_out, fbu, 'profile_information', 'profile_update_history.json')
    if os.path.isfile(posts_path):
        posts_json = open(posts_path).read()
        posts = json.loads(posts_json)['profile_updates']
        post_counter = 1
        rem_comments = []
        for post in posts:
            try:
                print('Parsing {0} of {1} updates...'.format(post_counter, len(posts)), flush=True)
                post_counter += 1
                # Extract comment details
                timestamp = datetime.fromtimestamp(post['timestamp'])
                if out_of_range(timestamp, months_back, last_date): continue
                post_date = timestamp.date()
                post_time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
                if 'title' in post:
                    caption = post['title']
                else:
                    continue

                location = 'Profile'
                media_dest = 'N/A'
                if 'attachments' not in post:
                    entry = [post_date, post_time, location, media_dest, caption, '', '']
                    posts_parsed.append(entry)
                else:
                    attachments = post['attachments'][0]['data']
                    for attachment in attachments:
                        if 'media' in attachment:
                            content = attachment['media']
                            media = content['uri']
                            friend_comments = ''
                            subject_comments = ''
                            if 'comments' in content:
                                for comment in content['comments']:
                                    if (display_name in comment['author']):
                                        subject_comments += '"' + scrubadub.clean(comment['comment']) + '", '
                                        rem_comments.append(comment['comment'])
                                    else:
                                        friend_comments += '"' + scrubadub.clean(comment['comment']) + '", '

                        scrubadub.clean(caption)
                        media_src = os.path.join(temp_out, fbu, media)
                        filename, file_extension = os.path.splitext(media)
                        if file_extension in supported_types:
                            media_id += 1
                            media_dest = os.path.join(media_root, '{0}{1}'.format(media_id, file_extension))
                            cv2.imwrite(media_dest, blur_faces(media_src))
                        entry = [post_date, post_time, location, media_dest, caption.encode('latin1').decode('utf8'), friend_comments.encode('latin1').decode('utf8'), subject_comments.encode('latin1').decode('utf8')]
                        posts_parsed.append(entry)

            except Exception as e:
                print("Error parsing FB profile update post: " + type(e).__name__ + ": {}".format(e))
                continue

    genCSV(fbu, 'posts.csv', posts_parsed)

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= FB COMMENTS =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    # Parse comments and likes
    print('Parsing {0}\'s comments and likes...'.format(display_name), flush=True)
    comments_path = os.path.join(temp_out, fbu, 'comments', 'comments.json')
    comments_parsed = [['Date', 'Time', 'Author', 'Subject Comment', 'Friend Timeline Comment', 'URL']]
    if os.path.isfile(comments_path):
        comments_json = open(comments_path).read()
        comments = json.loads(comments_json)['comments']
        for comment in comments:
            # Extract comment details
            try:
                timestamp = datetime.fromtimestamp(comment['timestamp'])
                if out_of_range(timestamp, months_back, last_date): continue
                comment_date = timestamp.date()
                comment_time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
                try: comment_attachment = comment['attachments'][0]['data'][0]['external_context']['url']
                except: comment_attachment = ""
                try:
                    cc = comment['data'][0]['comment']['comment']
                    if cc not in rem_comments:
                        comment_text = scrubadub.clean(cc)
                    else: continue
                except: comment_text = ""
                comments_parsed.append([comment_date, comment_time, 'Participant', comment_text.encode('latin1').decode('utf8'), '', comment_attachment])
            except Exception as e:
                print("Error parsing FB comment: " + type(e).__name__ + ": {}".format(e))
                continue

    timeline_path = os.path.join(temp_out, fbu, 'posts', 'other_people\'s_posts_to_your_timeline.json')
    if os.path.isfile(timeline_path):
        timeline_json = open(timeline_path).read()
        timeline = json.loads(timeline_json)['wall_posts_sent_to_you']
        # print(timeline)
        for timeline_post in timeline['activity_log_data']:
            try:
                # Extract comment details
                timestamp = datetime.fromtimestamp(timeline_post['timestamp'])
                if out_of_range(timestamp, months_back, last_date): continue
                timeline_post_date = timestamp.date()
                timeline_post_time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")

                if 'data' not in timeline_post:
                    continue

                attachment = ''
                if 'attachments' in timeline_post:
                    if 'data' in timeline_post['attachments'][0]:
                        if 'media' in timeline_post['attachments'][0]['data'][0]:
                            attachment = timeline_post['attachments'][0]['data'][0]['media']['uri']
                        elif 'external_context' in timeline_post['attachments'][0]['data'][0]:
                            attachment = timeline_post['attachments'][0]['data'][0]['external_context']['url']

                if 'post' not in timeline_post['data'][0]:
                    if attachment is not '':
                        comment_text = attachment
                    else:
                        continue
                else:
                    comment_text = timeline_post['data'][0]['post']

                comments_parsed.append([timeline_post_date, timeline_post_time, 'Friend', comment_text.encode('latin1').decode('utf8'), attachment])
            except Exception as e:
                print("Error parsing FB timeline post: " + type(e).__name__ + ": {}".format(e))
                continue

    genCSV(fbu, 'comments.csv', comments_parsed)

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= BEGIN =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= INSTAGRAM =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

# Parse Instagram files
for igu in unzip('instagram', temp_out):
    # Get display name
    profile_path = os.path.join(temp_out, igu, 'profile.json')
    profile_json = json.loads(open(profile_path).read())
    display_name = profile_json['name'] if 'name' in profile_json else ''
    user_name = profile_json['username']
    media_root = os.path.join(outbox_path, igu, 'media')
    pathlib.Path(media_root).mkdir(parents=True, exist_ok=True)

    print('Parsing {0}\'s Instagram...'.format(display_name), flush=True)
    months_back, last_date = ask_date()

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= IG COMMENTS =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    # Parse comments
    print('Parsing {0}\'s comments...'.format(display_name), flush=True)
    comments_path = os.path.join(temp_out, igu, 'comments.json')
    comments_json = open(comments_path, encoding='utf8').read()
    comments = json.loads(comments_json)
    comments_parsed = [['Date', 'Time', 'Subject\'s Photo', 'Friend\'s Photo']]
    for comment_sections in comments:
        for comment in comments[comment_sections]:
            try:
                timestamp = datetime.strptime(comment[0], '%Y-%m-%dT%H:%M:%S')
                if out_of_range(timestamp, months_back, last_date): continue
                post_date = timestamp.date()
                post_time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
                content = scrubadub.clean(comment[1])
                unrem = ''
                for word in content.split():
                    if word[0] is '@':
                        unrem += '{{USERNAME}} '
                    else:
                        unrem += word + ' '
                content = unrem
                author = comment[2]
                subject_comment = ''
                friend_comment = ''
                if (display_name in author):
                    subject_comment = content
                else:
                    friend_comment = content
                comments_parsed.append([post_date, post_time, subject_comment, friend_comment])
            except Exception as e:
                print("Error parsing IG comment: " + type(e).__name__ + ": {}".format(e))
                continue

    genCSV(igu, 'comments.csv', comments_parsed)

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-= IG FOLLOWERS =-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    # Parse followers / followees counts
    connections_path = os.path.join(temp_out, igu, 'connections.json')
    connections_json = open(connections_path, encoding='utf8').read()
    connections = json.loads(connections_json)

    follow_parsed = [
        ['Followers', 'Followees'],
        [len(connections['followers']), len(connections['following'])]
        ]

    genCSV(igu, 'following.csv', follow_parsed)

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= IG OFFLINE =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    if offline:
        # Parse posts
        posts_path = os.path.join(temp_out, igu, 'media.json')
        posts_json = json.loads(open(posts_path, encoding='utf8').read())
        posts = posts_json['photos']
        videos = posts_json['videos']

        post_counter = 1
        media_id = 0
        posts_parsed = [['Date', 'Time', 'Media', 'Caption']]
        unique_post_timestamps = {}  # timestamp -> [media_subroot, num pics in post]
        for i, post in enumerate(posts):
            try:

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= IG POSTS =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

                print('Parsing {0} of {1} photos...'.format(i+1, len(posts)), flush=True)
                # Parse timestamp
                timestamp = datetime.strptime(post['taken_at'], '%Y-%m-%dT%H:%M:%S')
                media_subroot = None
                num_pics_in_post = 0
                if timestamp in unique_post_timestamps:
                    # another photo from a previously parsed post (already within time range)
                    info = unique_post_timestamps[timestamp]
                    media_subroot = info[0]
                    info[1] += 1  # adding a pic to the directory
                    num_pics_in_post = info[1]

                if media_subroot is None: # first photo for a post
                    if out_of_range(timestamp, months_back, last_date): continue
                    post_date = timestamp.date()
                    post_time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
                    # add directory to media folder for this post
                    media_subroot = os.path.join(media_root, str(post_counter))
                    num_pics_in_post = 1
                    pathlib.Path(media_subroot).mkdir(parents=True, exist_ok=True)
                    unique_post_timestamps[timestamp] = [media_subroot, num_pics_in_post]
                    post_counter += 1
                    # Parse text
                    caption = scrubadub.clean(post['caption'])
                    entry = [post_date, post_time, media_subroot, caption.encode('latin1', 'ignore').decode('utf8')]
                    posts_parsed.append(entry)

                # Parse photo
                media = post['path']
                media_src = os.path.join(temp_out, igu, media)
                filename, file_extension = os.path.splitext(media)
                media_subdest = 'N/A'
                media_id = chr(97 - 1 + num_pics_in_post)
                if file_extension in supported_types:
                    media_subdest = os.path.join(media_subroot, '{0}{1}'.format(str(post_counter-1)+media_id, file_extension))
                    cv2.imwrite(media_subdest, blur_faces(media_src))


            except Exception as e:
                print("Error parsing IG media: " + type(e).__name__ + ": {}".format(e))
                continue

        # add text content of videos
        for i, video in enumerate(videos):
            print('Parsing {0} of {1} videos...'.format(i+1, len(videos)), flush=True)
            if video['taken_at'] not in unique_post_timestamps:  # make new row
                timestamp = datetime.strptime(video['taken_at'], '%Y-%m-%dT%H:%M:%S')
                if out_of_range(timestamp, months_back, last_date): continue
                video_date = timestamp.date()
                video_time = timestamp.strftime("%#I:%M %p") if platform.system() == 'Windows' else timestamp.strftime("%-I:%M %p")
                caption = scrubadub.clean(video['caption'])
                entry = [video_date, video_time, '', caption.encode('latin-1', 'ignore').decode('utf8')]
                posts_parsed.append(entry)


        # sort posts by timestamp
        posts_parsed[1:] = sorted(posts_parsed[1:], key=itemgetter(0,1), reverse=True)
        genCSV(igu, 'posts.csv', posts_parsed)

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= IG ONLINE =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    else:  # not offline, i.e. online
        # Pull Instagram data from web
        posts_parsed = [['Date', 'Time', 'Media', 'Caption', 'Likes', 'Comments']]
        L = instaloader.Instaloader()

        try:
            L.interactive_login(user_name)
        except Exception as e:
            print("Failed login with username from download: " + type(e).__name__ + ": {}".format(e))
            user_name = input('Please enter subject\'s Instagram username: ')
            L.interactive_login(user_name)

        profile = instaloader.Profile.from_username(L.context, user_name)
        posts = profile.get_posts()

        post_counter = 1
        print('Parsing {0}\'s media...'.format(display_name), flush=True)
        for post in posts:
            try:

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= IG POSTS =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

                if out_of_range(post.date, months_back, last_date): continue
                print('Parsing media number {0}...'.format(post_counter+1), flush=True)
                media_subroot = ''  # in case it's a video
                if post.typename == 'GraphSidecar' or post.typename == 'GraphImage':  # not video
                    media_subroot = os.path.join(media_root, str(post_counter))
                    pathlib.Path(media_subroot).mkdir(parents=True, exist_ok=True)
                    char_count = 97  # start at 'a'

                    if post.typename == 'GraphSidecar':
                        for n in post.get_sidecar_nodes():
                            if n.is_video: continue
                            media_subdest = os.path.join(media_subroot, str(post_counter)+chr(char_count))
                            with open(os.devnull, 'w') as devnull:  # to get rid of printing
                                with contextlib.redirect_stdout(devnull):
                                    L.download_pic(media_subdest, n.display_url, post.date, filename_suffix=None)
                            char_count += 1

                    elif post.typename == 'GraphImage':
                        media_subdest = os.path.join(media_subroot, str(post_counter)+chr(char_count))
                        with open(os.devnull, 'w') as devnull:  # to get rid of printing
                            with contextlib.redirect_stdout(devnull):
                                L.download_pic(media_subdest, post.url, post.date, filename_suffix=None)

                    post_counter += 1

                likes = post.likes
                time = post.date_local.strftime("%#I:%M %p") if platform.system() == 'Windows' else post.date_local.strftime("%-I:%M %p")
                date = post.date_local.date()
                unrem = ''
                if post.caption is not None:
                    for word in post.caption.split():
                        if word[0] is '@':
                            unrem += '{{USERNAME}} '
                        else:
                            unrem += word + ' '
                caption = scrubadub.clean(unrem)
                comments = ''
                for comment in post.get_comments():
                    unrem = ''
                    for word in comment[2].split():
                        if word[0] is '@':
                            unrem += '{{USERNAME}} '
                        else:
                            unrem += word + ' '
                    comments += '"' + scrubadub.clean(unrem) + '", '

                entry = [date, time, media_subroot, caption, likes, comments]
                posts_parsed.append(entry)
            except Exception as e:
                print("Error parsing IG media: " + type(e).__name__ + ": {}".format(e))
                continue

        print('Scrubbing {0}\'s media...'.format(display_name), flush=True)
        media_files = [f for f in glob.glob('./outbox/{0}_instagram/media/*/*'.format(user_name), recursive=True)]
        for filename in media_files:
            try:
                if any(filename.endswith(end) for end in supported_types):
                    cv2.imwrite(filename, blur_faces(filename))
            except Exception as e:
                print("Error scrubbing IG media: " + type(e).__name__ + ": {}".format(e))
                continue

        genCSV(igu, 'posts.csv', posts_parsed)

print('Cleaning up the temp folder...')
shutil.rmtree('./inbox/temp')
print('Done!')
