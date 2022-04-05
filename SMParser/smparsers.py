#smparser-classes2.py
#Parsing methods unique to each platform
#%%smparserbase
from collections import Counter
from datetime import datetime
import itertools
import logging
from pathlib import Path
import re

from dateutil import parser as dt_parser
import PySimpleGUI as sg
from .smparserbase import SMParserBase, Media

#%%
class FBParser(SMParserBase):
	'''Social Media Parser class for Facebook data, v2 Schema'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.scrubber_update()

	def parse_profile_metadata(self):
		logging.info('Parsing FB profile metadata')
		data = self.get_json('profile_information','profile_information')
		self.username = data.profile_v2.name.full_name
		return None

	def parse_friends(self):
		'''Parse FB Friends - Aggregated counts/totals'''
		logging.info(f'Parsing {self.username} FB friends metadata')
		data = self.get_json('friends_and_followers','friends')
		data2 = self.get_json('friends_and_followers','removed_friends')
		friends_header = ['Total Friends', 'Removed Friends']
		payload = [
			{'Total Friends': len(data.friends_v2), 
			'Removed Friends': len(data2.deleted_friends_v2)}]
		self.genCSV("FB_friends", friends_header, payload)
		return None
	
	def parse_reactions(self):
		'''Parse FB Reactions, aggregating totals by Type and Category'''
		logging.info(f'Parsing {self.username} FB reactions metadata')
		data = self.get_json('comments_and_reactions','posts_and_comments')
		categories = ['photo','comment','post','link','album','video','other']
		react_header = ['Type', 'Total']
		react_header.extend(categories)
		reactions = data.reactions_v2
		reaction_counts = dict()
		try:
			#.timestamp;  .title;   .data[0].reaction.reaction;  .data[0].reaction.actor
			#Per Client: Gather counts by type over the range; don't concat titles or agg by week (for now)
			#TODO: refactor this in Pandas pivot?
			reactions_inrange = [r for r in reactions if self.in_date_range(datetime.fromtimestamp(r.timestamp))]
			f_reaction_date = lambda r: (datetime.fromtimestamp(r.timestamp)).date()
			f_reaction_type = lambda r: r.data[0].reaction.reaction
			def f_extract_category(react, rcat='other'):
				for cat in categories:
					rcat = cat if cat in react else rcat 
				return rcat

			reactions_dicts = [{'Date': f_reaction_date(r), 'Type': f_reaction_type(r), 'Category': f_extract_category(r.title)} 
								for r in reactions_inrange]
			f_type = lambda r: r["Type"]
			reactions_sorted = sorted(reactions_dicts, key=f_type)
			reactions_by_type = itertools.groupby(reactions_sorted, key=f_type)
			reaction_counts = {rtype: dict(Counter([r['Category'] for r in rlist])) for rtype, rlist in reactions_by_type}
			reaction_totals = Counter(r['Type'] for r in reactions_dicts)
			for rtype, rc in reaction_counts.items():
				rc['Type'] = rtype
				rc['Total'] = reaction_totals[rtype]
		except Exception as e:
			logging.error(f'Error parsing FB reaction: {type(e).__name__}: {e}')
		self.genCSV("FB_reactions", react_header, list(reaction_counts.values()))
		return None
	
	def parse_posts(self):
		'''Parsing of Facebook posts; Scrubbing captions & blurring photos'''
		logging.info(f'Parsing {self.username} FB posts metadata')
		posts_header = ['Date', 'Time', 'Location', 'Post', 'Caption', 'Subject Comments', 'Friend Comments']
		posts = self.get_json('posts','your_posts_1')
		payload = list()
		for i, post in enumerate(posts):
			try:
				logging.debug(f'Parsing {i} of {len(posts)} FB posts...')
				caption = list()
				ts = post.timestamp
				pts, pdate, ptime = self.parse_time(ts)
				if not self.in_date_range(pts): continue
				if hasattr(post, 'data'):
					if len(post.data) > 0 and hasattr(post.data[0], 'post'):
						caption.append(self.clean_text(post.data[0].post))
				if hasattr(post, 'title'):
					caption.append(self.clean_text(post.title))
				payload.append({'Date': pdate, 'Time': ptime, 
								'Location': 'Profile', 'Post': 'N/A',
								'Caption': '; '.join(caption), 'Friend Comments': '',
								'Subject Comments': ''})
				if not hasattr(post, 'attachments') or len(post.attachments)==0:
					continue
				attachments = post.attachments[0].data
				for j, att in enumerate(attachments):
					if hasattr(att, 'media'):
						content = att.media
						media_fp = att.media.uri
						caption = [att.media.title]

						img_ext = self.parse_img_ext(Path(media_fp))
						if img_ext is None: continue
						out_path = self.media_path / 'FB' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
						ph = Media(media_fp, img_ext, pdate, ptime, out_path)
						self.posts_media.append(ph)
					elif hasattr(att, 'external_context'):
						content = att.external_context
						caption = [f': {content.uri}']
						media_fp = 'External'
						out_path = ''
					else:
						continue
					
					# Friend Comments, Subject Comments
					fc, sc = [], []
					if hasattr(content, 'description'):
						caption.append(self.clean_text(content.description))
					if hasattr(content, 'comments'):
						for comment in att.media.comments:
							if self.username in comment.author:
								sc.append(f'"{self.clean_text(comment.comment)}"')
								self.rem_comments.append(comment.comment)
							else:
								fc.append(f'"{self.clean_text(comment.comment)}"')
					payload.append({'Date': pdate, 'Time': ptime, 
									'Location': media_fp, 'Post': out_path, 
									'Caption': '; '.join(caption), 
									'Friend Comments': '; '.join(fc),
									'Subject Comments': '; '.join(sc)})
			except Exception as e:
				logging.error(f"Error parsing FB profile update post: {type(e).__name__}: {e}")
				continue
		self.genCSV("FB_posts", posts_header, payload)
		return None

	def parse_profile_updates(self):
		'''Parsing of Facebook profile updates; Scrubbing captions & blurring photos'''
		#Future TODO: Can this be consolidated with FB posts?
		logging.info(f'Parsing {self.username} FB profile updates metadata')
		posts_header = ['Date', 'Time', 'Location', 'Post', 'Caption', 'Subject Comments', 'Friend Comments']
		data = self.get_json('profile_information','profile_update_history')
		posts = data.profile_updates_v2
		payload = list()
		for i, post in enumerate(posts):
			try:
				logging.debug(f'Parsing {i} of {len(posts)} FB profile updates...')
				ts = post.timestamp
				pts, pdate, ptime = self.parse_time(ts)
				if not self.in_date_range(pts): continue
				if not hasattr(post, 'title'): continue
				caption = self.clean_text(post.title)
				payload.append({'Date': pdate, 'Time': ptime, 
								'Location': 'Profile', 'Post': 'N/A',
								'Caption': caption, 'Friend Comments': '',
								'Subject Comments': ''})
				if not hasattr(post, 'attachments'): continue
				attachments = post.attachments[0].data
				for j, att in enumerate(attachments):
					if not hasattr(att, 'media'): continue
					content = att.media
					media_fp = att.media.uri
					img_ext = self.parse_img_ext(Path(media_fp))
					if img_ext is None: continue
					#Friend Comments, Subject Comments
					fc, sc = [], []
					if hasattr(content, 'comments'):
						for comment in att.media.comments:
							if self.username in comment.author:
								sc.append(f'"{self.clean_text(comment.comment)}"')
								self.rem_comments.append(comment.comment)
								continue
							fc.append(f'"{self.clean_text(comment.comment)}"')

					out_path = self.media_path / 'FB' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
					self.posts_media.append(Media(media_fp, img_ext, pdate, ptime, out_path))
					payload.append({'Date': pdate, 'Time': ptime, 
									'Location': media_fp, 'Post': out_path, 
									'Caption': caption, 
									'Friend Comments': ';'.join(fc),
									'Subject Comments': ';'.join(sc)})
			except Exception as e:
				logging.error(f"Error parsing FB profile update post: {type(e).__name__}: {e}")
				continue
		self.genCSV("FB_profile_updates", posts_header, payload)
		return None

	def parse_comments(self):
		'''Parsing of FB Comments & Likes'''
		logging.info(f'Parsing {self.username} FB comments & likes metadata')
		data = self.get_json('comments_and_reactions','comments')
		comment_header = ['Date', 'Time', 'Author', 'Subject Comments', 'Friend Comments', 'URL']
		comments = data.comments_v2
		payload = []
		for comment in comments:
			try:
				ts = comment.timestamp
				cts, cdate, ctime = self.parse_time(ts)
				if not self.in_date_range(cts): continue
				comment_attachment = comment.attachments
				try:
					cc = comment.data[0].comment.comment
					if cc in self.rem_comments: continue
					comment_text = self.clean_text(cc)
				except:
					comment_text = ''
				payload.append({'Date': cdate, 'Time': ctime,
								'Author': 'Participant', 'Subject Comments': comment_text,
								'Friend Comments': '', 'URL': comment_attachment})
			except Exception as e:
				logging.error(f'Error parsing FB reaction: {type(e).__name__}: {e}')
				continue
		self.genCSV("FB_comments", comment_header, payload)
		return None

	def parse_data(self):
		self.rem_comments = list()
		self.parse_profile_metadata()
		self.parse_friends()
		self.parse_reactions()
		self.parse_posts()
		self.parse_profile_updates()
		if sg.popup_yes_no(f'Scrub & save {len(self.posts_media)} FB images?') == 'Yes':
			logging.info(f'Scrub & save {len(self.posts_media)} FB images')
			self.scrub_and_save_media(self.posts_media)
		return None

#%%
class IGParser(SMParserBase):
	'''Social Media Parser class for Instagram data, v2 Schema'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.scrubber_update()
    
	def parse_profile_metadata(self):
		logging.info('Parsing IG profile metadata')
		data = self.get_json('account_information','personal_information')
		self.username = data.profile_user[0].string_map_data.Username.value
		return None
	
	def parse_comments(self):
		'''Parsing of IG Comments with scrubbed content'''
		logging.info('Parsing IG comments')
		data = self.get_json('comments', 'post_comments')
		comments_header = ['Date', 'Time', 'Content']
		users_comments_on_own_post = []
		users_comments_on_other_post = []

		for comment in data.comments_media_comments:
			c0 = comment.string_list_data[0]
			ts = c0.timestamp
			comment_value = c0.value
			author = comment.title
			timestring, date, time = self.parse_time(ts)
			
			if not self.in_date_range(timestring): continue
			content = self.clean_text(comment_value)
			if re.compile(r'^\s*$').match(content): continue
			row = {"Date":date, "Time":time, "Content":content}
			if author == self.username:
				#if users_comments_on_own_post[-1][2] == content: continue
				users_comments_on_own_post.append(row)
			else:
				#if users_comments_on_other_post[-1][2] == content: continue
				users_comments_on_other_post.append(row)
		self.genCSV("IG_users_comments_on_own_post", comments_header, users_comments_on_own_post)
		self.genCSV("IG_users_comments_on_other_post", comments_header, users_comments_on_other_post)
		return None

	def parse_follow(self):
		'''Parsing followers - Aggregated Total counts'''
		logging.info("Parsing IG Follow")
		data = self.get_json('followers_and_following', 'followers')
		data2 = self.get_json('followers_and_following', 'following')
		follow_header = ['Followers', 'Following']
		payload = [
			{'Followers': len(data.relationships_followers), 
			'Following': len(data2.relationships_following)}]
		self.genCSV("IG_follow", follow_header, payload)
		return None

	def parse_posts(self):
		'''Parsing IG Posts - Indexing of Media paths in Posts & Stories'''
		logging.info('Parsing IG posts')
		posts_header = ["Date", "Time", "ImgPath", "Caption", "Likes", "Comments"]
		#--- PHOTOS
		posts_data = self.get_json("content", "posts_1")
		for i, post in enumerate(posts_data):
			ts = post.creation_timestamp if hasattr(post, 'creation_timestamp') else None
			comment = post.title if hasattr(post, 'title') else ""
			for j, photo in enumerate(post.media):
				ts = ts if ts is not None else photo.creation_timestamp
				pts, pdate, ptime = self.parse_time(ts)
				if not self.in_date_range(pts): continue
				comment += self.clean_text(photo.title)
				img_fp = photo.uri
				img_ext = self.parse_img_ext(Path(img_fp))
				if img_ext is None: continue
				out_path = self.media_path / 'IG' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
				self.posts_media.append(Media(img_fp, img_ext, pdate, ptime, out_path, comment))

		#--- STORIES
		logging.info("Parsing IG stories")
		stories_data = self.get_json("content", "stories")
		#sposts.ig_stories[0].uri
		valid_stories = [s for s in stories_data.ig_stories if self.in_date_range(datetime.fromtimestamp(s.creation_timestamp))]
		for i, story in enumerate(valid_stories):
			img_fp = story.uri
			sts, sdate, stime = self.parse_time(story.creation_timestamp)
			img_ext = self.parse_img_ext(Path(img_fp))
			if not self.in_date_range(sts) or img_ext is None: continue
			out_path = self.media_path / 'IG' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
			comment = self.clean_text(story.title)
			self.posts_media.append(Media(img_fp, img_ext, sdate, stime, out_path, comment))

		#--- PROFILE PICS
		logging.info("Parsing IG profile pic")
		profile_pic_data = self.get_json("content", "profile_photos")
		for i, photo in enumerate(profile_pic_data.ig_profile_picture):
			img_fp = photo.uri
			img_ext = self.parse_img_ext(Path(img_fp))
			out_path = self.media_path / 'IG' / f'Post{i}' / f'Photo_{i}_{self.ph_num(j)}{img_ext}'
			pts, pdate, ptime = self.parse_time(photo.creation_timestamp)
			comment = self.clean_text(photo.title)
			self.posts_media.append(Media(img_fp, img_ext, pdate, ptime, out_path, comment))
		
		#--- Build the csv
		logging.debug(self.posts_media)
		posts_row_data = [r.__dict__ for r in self.posts_media]
		self.genCSV("IG_Posts", posts_header, posts_row_data)
		return None

	def parse_data(self):
		self.parse_profile_metadata()
		self.parse_follow()
		self.parse_comments()
		self.parse_posts()
		if sg.popup_yes_no(f'Scrub & save {len(self.posts_media)} IG images?') == 'Yes':
			logging.info(f'Scrub & save {len(self.posts_media)} IG images')
			self.scrub_and_save_media(self.posts_media)
		return None

#%%
class TTParser(SMParserBase):
	'''Parser class for TikTok user data'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.scrubber_update()

	def parse_profile_metadata(self):
		logging.info('Parsing TT profile metadata')
		data = (self.get_txt('Profile','Profile Info'))[0]
		header = ['Profile Item', 'Value']
		self.username = data["Username"]
		data['Birthdate'] = '{{BIRTHDAY}}'
		payload = [{'Profile Item':k, 'Value': self.clean_text(v)} for k,v in data.items()] 
		self.genCSV('TT_Profile', header, payload)
		return None

	def filter_by_date(self, data):     #data: list[dict{'Date'}]
		'''Parses the string date into a Datetime, filters down to records within date range'''
		#_dated_data = [c.update(Date = dt_parser.parse(c['Date'])) for c in data]
		return [c for c in data if self.in_date_range(dt_parser.parse(c['Date']))]

	def parse_follow(self):
		'''Parsing TT follow activity - Aggregated Total counts'''
		logging.info('Parsing TT Follow')
		header = ['Followers', 'Following']
		#Follower.txt -> {Date, Username}
		#Following.txt -> {Date, Username}
		data = self.get_txt('Activity', 'Follower')
		fdata = self.filter_by_date(data)
		data2 = self.get_txt('Activity', 'Following')
		fdata2 = self.filter_by_date(data2)
		payload = [
			{'Followers': len(fdata), 
			'Following': len(fdata2)}]
		self.genCSV('TT_follow', header, payload)
		return None

	def parse_hashtags(self):
		'''Parsing TT Hashtags - List of Hashtags with favorites noted'''
		logging.info('Parsing TT Hashtags')
		header = ['Hashtag Name', 'Hashtag Link', 'Favorite']
		#Hashtag.txt -> {Hashtag Name, Hashtag Link}
		#Favorite HashTags.txt -> {Hashtag Name, Hashtag Link}
		data = self.get_txt('Activity', 'Hashtag')
		data2 = self.get_txt('Activity', 'Favorite HashTags')
		#Note: No dates/times
		fht = [ht['Hashtag Name'] for ht in data2]
		for ht in data:
			ht['Favorite'] = 'Yes' if (ht['Hashtag Name'] in fht) else ''
		self.genCSV('TT_hashtags', header, data)
		return None

	def parse_user_searches(self):
		'''Parsing TT Search activity - List of Searches by date/time'''
		#Searches.txt -> {Date, Search Term}
		logging.info('Parsing TT Search Activity')
		header = ['Date', 'Search Term']
		data = self.get_txt('Activity', 'Searches')
		#Filter within date range
		searches = self.filter_by_date(data)
		scrub = lambda c: c.update({'Search Term': self.clean_text(c['Search Term'])})
		map(scrub, searches)
		self.genCSV('TT_searches', header, searches)
		return None

	def parse_user_likes(self):
		'''Parsing TT Like activity - List of Likes by date/time'''
		#Likes.txt -> {Date, Video Link}
		logging.info('Parsing TT Search Activity')
		header = ['Date', 'Video Link']
		data = self.get_txt('Activity', 'Likes')
		#Filter within date range
		payload = self.filter_by_date(data)
		self.genCSV('TT_likes', header, payload)
		return None

	def parse_video_browsing(self):
		'''Parsing TT video browsing activity'''
		logging.info('Parsing TT video Activity')
		#Video Browsing.txt -> {Date, Video Link}
		#Favorite Videos.txt -> {Date, Video Link}
		header = ['Date', 'Video Link', 'Favorite']
		data = self.get_txt('Activity', 'Video Browsing')
		data2 = self.get_txt('Activity', 'Favorite Videos')
		data3 = self.get_txt('Activity', 'Likes')
		#Filter within date range & correlate Favs + Likes
		fvids = self.filter_by_date(data)
		fav = [vid['Video Link'] for vid in data2]
		lk = [vid['Video Link'] for vid in data3]
		for vid in fvids:
			vid['Favorite'] = 'Yes' if (vid['Video Link'] in fav) else ''
			vid['Liked'] = 'Yes' if (vid['Video Link'] in lk) else ''
		self.genCSV('TT_video_browing', header, fvids)
		return None

	def parse_comments_from_others(self):
		'''Parsing TT Comments from others'''
		# Comments.txt -> {Date, Comment}
		logging.info('Parsing TT Comments from others')
		header = ['Date', 'Comment']
		data = self.get_txt('Comments', 'Comments')
		#Filter within date range & scrub comment
		all_comments = self.filter_by_date(data)
		scrub = lambda c: c.update({'Comment': self.clean_text(c['Comment'])})
		map(scrub, all_comments)
		self.genCSV('TT_comments', header, all_comments)
		return None

	def parse_user_videos(self):
		'''Parsing TT Videos posted by User'''
		# Videos.txt -> {Date, Video Link, Like(s)}
		logging.info('Parsing TT Videos posted by user')
		header = ['Date', 'Video Link', 'Like(s)']
		data = self.get_txt('Videos', 'Videos')
		#Filter within date range
		payload = self.filter_by_date(data)
		self.genCSV('TT_videos', header, payload)
		return None

	def parse_data(self):
		self.parse_profile_metadata()
		self.parse_follow()
		self.parse_hashtags()
		self.parse_user_searches()
		self.parse_user_likes()
		self.parse_video_browsing()
		self.parse_comments_from_others()
		self.parse_user_videos()
		# Note: No 'media' to scrub
	'''
    App Settings\Block List.txt
  X  Activity\Favorite HashTags.txt
  X  Activity\Hashtag.txt
  X  Activity\Follower.txt
  X  Activity\Following.txt
  X  Activity\Likes.txt
  X  Comments\Comments.txt
  X  Videos\Videos.txt
  X  Profile\Profile Info.txt
  X  Activity\Searches.txt
  X  Activity\Favorite Videos.txt''' 

'''TikTok
  X  participant's profile = Profile --> Profile Info
  X  comments that others have posted on participants posts = Comments
  X  most used hashtags = Activity --> Favorite HashTags
  X  number of followers/following/blocked users =  Activity --> Follower, Following
  X  search history =  Activity --> Searches
  X  most watched videos = Activity --> Favorite Videos
  X  time stamps from when videos were posted or browsed = ??
  X  number of likes on participant's posts =  Activity --> Likes
    '''
#%%
class SCParser(SMParserBase):
    '''Parser class for SnapChat data'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scrubber_update()

    def parse_profile_metadata(self):
        logging.info('Parsing SC profile metadata')
        data = self.get_json('','user_profile')
        header = ['Profile Item', 'Value']
        self.username = data["Username"]
        data['Birthdate'] = '{{BIRTHDAY}}'
        payload = [{'Profile Item':k, 'Value': self.scrubber.clean(v)} for k,v in data] 
        self.genCSV('SC_Profile', header, payload)
        return None

    def parse_follow(self):
        '''Parsing SC followers - Aggregated Total counts'''
        logging.info("Parsing SC Follow")
        data = self.get_json('', 'friends')
        #data2 = self.get_json('followers_and_following', 'following')
        header = ['Friends', 'Blocked', 'Pending']
        payload = [ {'Friends': len(data.friends)},
                    {'Blocked': len(data.blocked)},
                    {'Pending': len(data.pending)}] 
        self.genCSV("SC_follow", header, payload)

    def parse_friends(self):
        '''Parse SC Friends - Aggregated counts/totals'''
        logging.info(f'Parsing {self.username} SC friends metadata')
        data = self.get_json('json','friends')
        #data2 = self.get_json('friends_and_followers','removed_friends')
        header = ['Total Friends', 'Removed Friends']
        payload = [
            {'Total Friends': len(data.friends), 
            'Removed Friends': ''}]  #len(data2.deleted_friends_v2)}]
        self.genCSV("FB_friends", header, payload)
        return None
    '''
   X friends.json
    ranking.json
    story_history.json
    talk_history.json
   X user_profile.json
    ?Public profile?'''

    '''Snapchat: 

    time spent on app = ??
    type of content participant is interacting with = ranking.json OR user_profile.json under "Discover Channels Viewed" and "Interest Categories" OR subscriptions.json "
   X number of followers = friends.json
    number of views on participant's posts = story_history.json
   X friend requests sent, deleted users and blocked users, and ignored snapchatters by participant = ??'''