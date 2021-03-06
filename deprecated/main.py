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
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError

import social_keys
import model
import os,logging,re,sys
import datetime,time
import cache_keys
import helpers

from django.utils import simplejson as json

sys.path.insert(0, 'tweepy')

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError

FAILURE_NO_USER_CODE = 1
FAILURE_NO_USER_TEXT = "User is not setup"

FAILURE_NO_TEXT_TO_SAVE_CODE = 2
FAILURE_NO_TEXT_TO_SAVE_TEXT = "Text to save is not correct"

FAILURE_CAPABILITY_DISABLED_CODE = 3
FAILURE_CAPABILITY_DISABLED_TEXT = "Capability disabled error, try back later"

URL_STATIC_ERROR_DEFAULT = "/static/default_error.html"

class FailureJson(object):
    def __init__(self,failure_key,failure_message):
        self.failure_key = failure_key
        self.failure_message = failure_message
        
    def get_json(self):
        return json.dumps({"success" : False, "failure_key" : self.failure_key, "failure_message" : self.failure_message});


class GetDemoPostsHandler(webapp.RequestHandler):
    def get(self): 
        util = helpers.Util()
        user_model = util.is_user_good()
    
        #if not user_model == None:
        _template_values = {}
         
        posts_results_cache_key = cache_keys.POSTS_DEMO
        cache_results = memcache.get(posts_results_cache_key)
        
        if not cache_results == None:
            logging.info("cached search results being returned for key: %s" % posts_results_cache_key)
            _template_values["r"] = cache_results
        else:
            logging.info("search results not found for cache key %s" % posts_results_cache_key)
            queries = helpers.Queries()
            q = queries.get_posts_demo()
            results = q.fetch(10, config=queries.get_db_run_config_eventual() )
            
            _template_values["r"] = results
            memcache.add(posts_results_cache_key, _template_values["r"], 3600)
        
        _path = os.path.join(os.path.dirname(__file__), 'posts_demo.html') 
        
        self.response.headers["Expires"] = util.get_expiration_stamp(3600)
        self.response.headers["Content-Type"] = "application/json"
        self.response.headers["Cache-Control: max-age"] = 3600
        self.response.headers["Cache-Control"] = "public"
        self.response.out.write(template.render(_path, _template_values))
             
        #else:
        #    fail = FailureJson(FAILURE_NO_USER_CODE,FAILURE_NO_USER_TEXT)
        #    self.response.out.write( fail.get_json() )

class GetPostsHandler(webapp.RequestHandler):
    def get(self): 
    
        util = helpers.Util()
        user_model = util.is_user_good()
    
        if not user_model == None:
            
            _template_values = {}
            
            get_which = self.request.get("which")
            get_since = self.request.get("since")
            
            if get_since == "" or get_since == "undefined": get_since = None
            
            day_start = util.get_todays_start()
            day_stop = util.get_todays_stop()

            _template_values["day_start"] = day_start
            _template_values["day_stop"] = day_stop
            
            posts_results_cache_key = cache_keys.POST_RESULTS % (get_which,get_since,day_start.date())
            
            logging.info("post results cache key is: %s" % posts_results_cache_key)
            cache_results = memcache.get(posts_results_cache_key)
            
            if not cache_results == None:
                logging.info("cached search results being returned for key: %s" % posts_results_cache_key)
                _template_values["c"] = get_since
                _template_values["r"] = cache_results
                
            else:
                logging.info("search results not found for cache key %s" % posts_results_cache_key)
                
                queries = helpers.Queries()
                
                if get_which == "yours-pending": 
                    
                    q = queries.get_posts_yours_pending(user_model,get_since,day_start)
                    results = q.fetch(100, config= queries.get_db_run_config_eventual() )
                    cursor = q.cursor()
                    
                    if get_since == None: 
                        q2 = queries.get_posts_yours_resubmitted(user_model,day_start)
                        results2 = q2.fetch(100, config= queries.get_db_run_config_eventual())
                        logging.info("yours resubmitted: %s" % len(results2) )
                        results.extend(results2 )
                    
                    _template_values["c"] = cursor
                    _template_values["r"] = results
                    
                elif get_which == "theirs-pending":
                    q = queries.get_posts_theirs_pending(get_since,day_start)
                    results = q.fetch(100, config= queries.get_db_run_config_eventual())
                    cursor = q.cursor()
                    
                    if get_since == None: 
                        q2 = queries.get_posts_theirs_resubmitted(user_model,day_start)
                        results2 = q2.fetch(100, config= queries.get_db_run_config_eventual())
                        logging.info("theirs resubmitted: %s" % len(results2) )
                        results.extend( results2 )
                    
                    _template_values["c"] = cursor
                    _template_values["r"] = results
                    
                else:
                    logging.warning("unknown which was passed: %" % get_which)
                    _template_values["c"] = None
                    _template_values["r"] = None
                    
            if not _template_values["r"] == None:
                memcache.add(posts_results_cache_key, _template_values["r"], 60)

            _path = os.path.join(os.path.dirname(__file__), 'posts.html') 
            
            self.response.headers["Expires"] = util.get_expiration_stamp(60)
            self.response.headers["Content-Type"] = "application/json"
            self.response.headers["Cache-Control: max-age"] = 60
            self.response.headers["Cache-Control"] = "public"
            self.response.out.write(template.render(_path, _template_values))
            
        else:
            fail = FailureJson(FAILURE_NO_USER_CODE,FAILURE_NO_USER_TEXT)
            self.response.out.write( fail.get_json() )

class SavePostForMixHandler(webapp.RequestHandler):
    
    def get(self):
        self.redirect("/")
    
    def post(self):
        util = helpers.Util()
        user_model = util.is_user_good()
        
        self.response.headers["Content-Type"] = "application/json"
        
        if not user_model == None:
            text_to_save =self.request.get("text",  default_value=None)
            resubmit_post = self.request.get("resubmit",default_value="true")   
            resubmit_bool = resubmit_post.lower() in ("yes", "true", "t", "1")
            
            if not text_to_save == None and len(text_to_save) > 0 and len(text_to_save) < 140:
                day_created = util.get_todays_start()
                
                text_to_save = re.sub("\s+"," ",text_to_save)
                
                social_post = model.SocialPostsForUsers(social_user=user_model,text=text_to_save,day_created=day_created,resubmit=resubmit_bool)
                
                try:
                    social_post.put()
                    
                    self.response.out.write(json.dumps( { "success" : True, "id" : "%s" % social_post.key() }) )
                except CapabilityDisabledError:
                    fail = FailureJson(FAILURE_CAPABILITY_DISABLED_CODE,FAILURE_CAPABILITY_DISABLED_TEXT)
                    self.response.out.write( fail.get_json() )
            else:
                fail = FailureJson(FAILURE_NO_TEXT_TO_SAVE_CODE,FAILURE_NO_TEXT_TO_SAVE_TEXT)
                self.response.out.write( fail.get_json() )
            
        else:
            fail = FailureJson(FAILURE_NO_USER_CODE,FAILURE_NO_USER_TEXT)
            self.response.out.write( fail.get_json() )

class MainHandler(webapp.RequestHandler):
    
    def get(self):
        try:
            _template_values = self.get_template_state_for_user()
            _path = os.path.join(os.path.dirname(__file__), 'main.html')
            self.response.out.write(template.render(_path, _template_values))
        except CapabilityDisabledError:
            self.redirect(URL_STATIC_ERROR_DEFAULT)
    
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
            auth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET,"https://%s/callback" % self.request.host)
            redirect_url = auth.get_authorization_url()
            
            user_model.request_token_key = auth.request_token.key
            user_model.request_token_secret = auth.request_token.secret
            user_model.put()
        
            
        _template_values["redirect_url"] = redirect_url
        
        _template_values["logout_url"] = users.create_logout_url("/")
        _template_values["login_url"] = users.create_login_url("/")
        _template_values["user"] = user
        _template_values["user_model"] = user_model
        
        util = helpers.Util()
        
        _template_values["next_mix_run_time"] = util.get_next_mix_runtime()
        _template_values["current_server_time"] = util.get_current_time_for_show()
        
        return _template_values
        
class CallbackHandler(webapp.RequestHandler):
    def get(self):
        verifier = self.request.GET.get('oauth_verifier')
        
        user = users.get_current_user()
        
        if not user: 
            logging.warning("current user is not logged in")
            self.redirect("/")
        
        logging.info("running callback for user: %s" % user.user_id())
        
        social_users = model.SocialKeysForUsers.all()
        social_users.filter("user_id =",user.user_id())
        
        user_model = social_users.get()
        
        if not user_model == None and user_model.request_token_key and user_model.request_token_secret:
            try:
                auth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
                auth.set_request_token(user_model.request_token_key, user_model.request_token_secret)
                
                auth.get_access_token(verifier)
                
                user_model.access_token_key = auth.access_token.key
                user_model.access_token_secret = auth.access_token.secret
                
                api = API(auth)
                api_is_working = api.test()
                
                user_model.shortcut_social_username = api.me().screen_name
                
                user_model.put()
                
                memcache.add("twitter_user:%s" % user.user_id(), user_model.shortcut_social_username, 60)
                
                #self.response.out.write("twitter user name: %s\n" % user_model.shortcut_social_username)
                
                logging.debug("user access tokens have been set")
            
                self.redirect("/")
                
            except TweepError:
                logging.error( "TweepError error API is could not fetch me: %s" % user.user_id())
                
                user_model.access_token_key = None
                user_model.access_token_secret = None
                user_model.put()
                
                self.redirect(URL_STATIC_ERROR_DEFAULT)
            except CapabilityDisabledError:
                logging.error( "Capability Disabled Error could not write for: %s" % user.user_id())
                self.redirect(URL_STATIC_ERROR_DEFAULT)
        
        else: 
            logging.warning("user model is not setup correctly: %s for user % "  % (user_model, user.user_id()))
            self.redirect("/")
    
    
class MainMobileHandler(MainHandler):  
    def get(self):
        try:
            _path = os.path.join(os.path.dirname(__file__), 'mobile.html')
            _template_values = self.get_template_state_for_user()
            self.response.out.write(template.render(_path, _template_values))
        except CapabilityDisabledError:
            self.redirect(URL_STATIC_ERROR_DEFAULT)


#application = webapp.WSGIApplication([('/', MainMobileHandler),
#        ('/callback', CallbackHandler),
#        ('/saveformix',SavePostForMixHandler),
#        ('/getposts',GetPostsHandler),
#         ('/getdemoposts',GetDemoPostsHandler),
#        ],
#     debug=True)

def main():
    #util.run_wsgi_app(application)
    pass


if __name__ == '__main__':
    main()
