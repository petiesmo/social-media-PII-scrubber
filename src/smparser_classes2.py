from smparser_classes import SMParser

class TTParser(SMParser):
    '''Parser class for TikTok user data'''
    def __init__(self, person_name, person_alias, zip_path, home_dir=None):
        pass

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