from google.appengine.ext import db

class SocialKeysForUsers(db.Model):
    user_id = db.StringProperty(required=True)
    access_token_key = db.StringProperty()
    access_token_secret = db.StringProperty()
    request_token_key = db.StringProperty()
    shortcut_social_username = db.StringProperty()
    request_token_secret = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
class SocialPostsForUsers(db.Model):
    social_user = db.ReferenceProperty(SocialKeysForUsers,collection_name='social_user',required=True)
    day_created = db.DateTimeProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    text = db.StringProperty(required=True)
    
class SocialPostMixesForUsers(db.Model):
    origin_post = db.ReferenceProperty(SocialPostsForUsers,collection_name='origin_post',required=True)
    posted_to_user = db.ReferenceProperty(SocialKeysForUsers,collection_name='posted_to_user',required=True)
    posted_from_user = db.ReferenceProperty(SocialKeysForUsers,collection_name='posted_from_user',required=True)
    posted_to_twitter = db.BooleanProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)