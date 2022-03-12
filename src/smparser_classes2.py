from smparser_classes import SMParser

class TTParser(SMParser):
    '''Parser class for TikTok user data'''
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass

    def parse_profile_metadata(self):
        logging.info('Parsing TT profile metadata')
        data = self.get_txt('Profile','Profile Info')
        header = data.keys()
        self.username = data["Username"]
        self.genCSV('TT_Profile', header, data)
        return None
		
    def parse_follow(self):
        '''Parsing followers - Aggregated Total counts'''
        logging.info("Parsing TT Follow")
        data = self.get_txt('Activity', 'Follower')
        data2 = self.get_txt('Activity', 'Following')
        follow_header = ['Followers', 'Following']
        payload = [
            {'Followers': len(data), 
            'Following': len(data2)}]
        self.genCSV("TT_follow", follow_header, payload)
        return None

    def parse_hashtags(self):
        '''Parsing Hashtags'''
        logging.info("Parsing TT Hashtags")
        data = self.get_txt('Activity', 'Hashtag')
        data2 = self.get_txt('Activity', 'Favorite HashTags')
        hashtag_header = ['Favorite', 'Hashtag Name', 'Hashtag Link']
        payload = data
        self.genCSV("TT_follow", hashtag_header, payload)
        return None
    '''
    App Settings\Block List.txt
    Activity\Favorite HashTags.txt
    Activity\Hashtag.txt
    Activity\Follower.txt
    Activity\Following.txt
    Activity\Likes.txt
    Comments\Comments.txt
    Videos\Videos.txt
    Profile\Profile Info.txt
    Activity\Searches.txt
    Activity\Favorite Videos.txt''' 

    '''TikTok
    participant's profile = Profile --> Profile Info
    comments that others have posted on participants posts = Comments
    most used hashtags = Activity --> Favorite HashTags
    number of followers/following/blocked users =  Activity --> Follower, Following
    search history =  Activity --> Searches
    most watched videos = Activity --> Favorite Videos
    time stamps from when videos were posted or browsed = ??
    number of likes on participant's posts =  Activity --> Likes
    '''

class SCParser(SMParser):
    '''Parser class for SnapChat data'''
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass 
    '''
    friends.json
    ranking.json
    story_history.json
    talk_history.json
    user_profile.json
    ?Public profile?'''

    '''Snapchat: 

    time spent on app = ??
    type of content participant is interacting with = ranking.json OR user_profile.json under "Discover Channels Viewed" and "Interest Categories" OR subscriptions.json "
    number of followers = friends.json
    number of views on participant's posts = story_history.json
    friend requests sent, deleted users and blocked users, and ignored snapchatters by participant = ??'''