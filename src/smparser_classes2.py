from smparser_classes import SMParser

class TTParser(SMParser):
    '''Parser class for TikTok user data'''
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass

	def parse_profile_metadata(self):
		logging.info('Parsing TT profile metadata')
		data = self.get_txt('Profile','Profile Info')
		self.username = data["username"]
		self.genCSV('TT_Profile',header,data)
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