#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.api import memcache

import social_keys
import model
import os,logging
import datetime,time

from django.utils import simplejson as json

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError


FAILURE_NO_USER_CODE = 1
FAILURE_NO_USER_TEXT = "User is not setup"

FAILURE_NO_TEXT_TO_SAVE_CODE = 2
FAILURE_NO_TEXT_TO_SAVE_TEXT = "Text to save is not correct"


class Util(object):
    
    def is_user_good(self):
        user = users.get_current_user()
        if user:
            social_users = model.SocialKeysForUsers.all()
            social_users.filter("user_id =",user.user_id())
            user_model = social_users.get()
            
            if user_model.access_token_key and user_model.access_token_secret:
                return user_model
            else:
                return None
        else:
            return None
            
    def get_twitter_user(self,api,user):
        twitter_user = memcache.get("twitter_user:%s" % user.user_id())
                        
        if twitter_user == None:
            twitter_user = api.me()
            memcache.add("twitter_user:%s" % user.user_id(), twitter_user, 60)
        
        return twitter_user
    

class FailureJson(object):
    def __init__(self,failure_key,failure_message):
        self.failure_key = failure_key
        self.failure_message = failure_message
        
    def get_json(self):
        return json.dumps({"success" : False, "failure_key" : self.failure_key, "failure_message" : self.failure_message});


class GetPostsHandler(webapp.RequestHandler):
    def get(self): 
    
        util = Util()
        user_model = util.is_user_good()
    
        if not user_model == None:
            
            _template_values = {}
            
            dt = datetime.datetime.fromtimestamp(time.time())
            day_start = datetime.datetime(dt.year, dt.month, dt.day, hour=0,minute=0)
            day_stop = datetime.datetime(dt.year, dt.month, dt.day, hour=23,minute=59,second=59,microsecond=999999)
    
            _template_values["day_start"] = day_start
            _template_values["day_stop"] = day_stop
    
            get_which = self.request.get("which")
            get_since = self.request.get("since")
            
            q = model.SocialPostsForUsers.all()
            q.filter("day_created =",day_start)
            
            if not get_since == None:
                q.with_cursor(get_since)
            
            if get_which == "yours-pending":               
                q.filter("social_user =",user_model)
                q.order("created")
                results = q.fetch(100)
                cursor = q.cursor()
                
                _template_values["c"] = cursor
                _template_values["r"] = results
                
            elif get_which == "theirs-pending":
                q.order("created")
                results = q.fetch(100)
                cursor = q.cursor()
                
                _template_values["c"] = cursor
                _template_values["r"] = results
                
            else:
                pass

            _path = os.path.join(os.path.dirname(__file__), 'posts.html') 
            self.response.headers["Content-Type"] = "application/json"
            self.response.out.write(template.render(_path, _template_values))
            
        else:
            fail = FailureJson(FAILURE_NO_USER_CODE,FAILURE_NO_USER_TEXT)
            self.response.out.write( fail.get_json() )

class SavePostForMixHandler(webapp.RequestHandler):
    
    def get(self):
        self.redirect("/")
    
    def post(self):
        util = Util()
        user_model = util.is_user_good()
        
        self.response.headers["Content-Type"] = "application/json"
        
        if not user_model == None:
            text_to_save =self.request.get("text",  default_value=None)
            
            if not text_to_save == None and len(text_to_save) > 0 and len(text_to_save) < 140:
                dt = datetime.datetime.fromtimestamp(time.time())
                day_created = datetime.datetime(dt.year, dt.month, dt.day, hour=0,minute=0)
                social_post = model.SocialPostsForUsers(social_user=user_model,text=text_to_save,day_created=day_created)
                social_post.put()
                
                self.response.out.write(json.dumps( { "success" : True }) )
                
            else:
                fail = FailureJson(FAILURE_NO_TEXT_TO_SAVE_CODE,FAILURE_NO_TEXT_TO_SAVE_TEXT)
                self.response.out.write( fail.get_json() )
            
        else:
            fail = FailureJson(FAILURE_NO_USER_CODE,FAILURE_NO_USER_TEXT)
            self.response.out.write( fail.get_json() )

class MainHandler(webapp.RequestHandler):
    
    def get(self):
        _template_values = self.get_template_state_for_user()
        _path = os.path.join(os.path.dirname(__file__), 'main.html')
        self.response.out.write(template.render(_path, _template_values))
    
    def get_template_state_for_user(self):
        _template_values = {}
        user = users.get_current_user()
        
        user_model = None
        
        if user:
            logging.info("user: %s",user.nickname)
            social_users = model.SocialKeysForUsers.all()
            social_users.filter("user_id =",user.user_id())
            user_model = social_users.get()
            
            if not user_model == None:
                
                if user_model.access_token_key and user_model.access_token_secret:
                    _template_values["needs_twitter_auth"] = False
                    
                    auth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
                    auth.set_access_token(user_model.access_token_key,user_model.access_token_secret)
                    
                    api = API(auth)
                    api_is_working = api.test()
                    
                    if not api_is_working:
                        logging.warning("api is NOT working: %s",api_is_working)
                    
                    try:
                        twitter_user = memcache.get("twitter_user:%s" % user.user_id())
                        
                        if twitter_user == None:
                            twitter_user = api.me()
                            memcache.add("twitter_user:%s" % user.user_id(), twitter_user, 60)
                        
                        logging.info(twitter_user)
                        _template_values["twitter_user"] = twitter_user
                        
                    except TweepError:
                        logging.error( "TweepError error has occured, clearing access tokents")
                        user_model.access_token_key = None
                        user_model.access_token_secret = None
                        user_model.put()
                        
                        _template_values["needs_twitter_auth"] = True
                
                else:
                    _template_values["needs_twitter_auth"] = True
            
            else:
                _template_values["needs_twitter_auth"] = True
                user_model = model.SocialKeysForUsers(user_id=user.user_id())
                user_model.put()
            
        else:
            _template_values["needs_twitter_auth"] = True
            logging.warning("user is empty")
            
            
            
        redirect_url = None
        if _template_values["needs_twitter_auth"] and not user_model == None:
            auth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET,"http://localhost:8084/callback")
            redirect_url = auth.get_authorization_url()
            
            user_model.request_token_key = auth.request_token.key
            user_model.request_token_secret = auth.request_token.secret
            user_model.put()
        
            
        _template_values["redirect_url"] = redirect_url
        
        _template_values["logout_url"] = users.create_logout_url("/")
        _template_values["login_url"] = users.create_login_url("/")
        _template_values["user"] = user
        _template_values["user_model"] = user_model
        
        #_path = os.path.join(os.path.dirname(__file__), 'main.html')
        #self.response.out.write(template.render(_path, _template_values))
        
        return _template_values
        
class CallbackHandler(webapp.RequestHandler):
    def get(self):
        verifier = self.request.GET.get('oauth_verifier')
        auth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        user = users.get_current_user()
        
        if not user: 
            logging.warning("current user is not logged in")
            self.redirect("/")
        
        social_users = model.SocialKeysForUsers.all()
        social_users.filter("user_id =",user.user_id())
        user_model = social_users.get()
        
        #logging.info(user_model.usernickname)
        
        if not user_model == None and user_model.request_token_key and user_model.request_token_secret:
            auth.set_request_token(user_model.request_token_key, user_model.request_token_secret)
            
            auth.get_access_token(verifier)
            
            user_model.access_token_key = auth.access_token.key
            user_model.access_token_secret = auth.access_token.secret
            
            api = API(auth)
            api_is_working = api.test()
            
            user_model.shortcut_social_username = api.me().screen_name
            
            user_model.put()
            
            self.response.out.write("twitter api is working?: %s\n" % api_is_working)
            
            try:
                twitter_user = api.me()
                
                memcache.add("twitter_user:%s" % user.user_id(), twitter_user, 60)
                
                self.response.out.write("twitter user name: %s\n" % twitter_user.screen_name)
            except TweepError:
                logging.error( "TweepError error API is could not fetch me")
                #self.response.out.write("TweepError: %s" % err.reason)
            
            logging.debug("user access tokens have been set")
            
            self.redirect("/")
        
        else: 
            logging.warning("user model is not setup correctly: %s", user_model)
            #self.redirect("/")
    
    
class MainMobileHandler(MainHandler):  
    def get(self):
        _path = os.path.join(os.path.dirname(__file__), 'mobile.html')
        _template_values = self.get_template_state_for_user()
        self.response.out.write(template.render(_path, _template_values))

def main():
    application = webapp.WSGIApplication([('/', MainMobileHandler),
                                            ('/callback', CallbackHandler),
                                            ('/saveformix',SavePostForMixHandler),
                                            ('/getposts',GetPostsHandler),
                                            #('/mobile', MainMobileHandler)
                                            ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
