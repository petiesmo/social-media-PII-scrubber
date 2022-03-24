#%%
#smparser-classes2.py
from smparser_classes import SMParser
import logging
from dateutil import parser as dt_parser
#%%
class TTParser(SMParser):
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
        payload = self.filter_by_date(data)
        self.genCSV('TT_searches', header, payload)
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
        _payload = [c.update(Comment = self.clean_text(c['Comment'])) for c in all_comments]
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
class SCParser(SMParser):
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
