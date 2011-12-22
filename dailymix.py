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
from google.appengine.ext import db

import social_keys
import model
import os,logging
import datetime,time
import random

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError

class DailyMixHandler(webapp.RequestHandler):
    
    def perform_mix(self,user_list,post_list,api,move_to):
    
        logging.info("list sized for users and posts are: %s" % len(user_list))
        
        if len(user_list) > 1:
        
            logging.info("starting user and post list shuffle")
            random.shuffle(user_list)
            random.shuffle(post_list)
            
            logging.info("done with user and post list shuffle")        
            
            logging.info("starting mix assignments")
            
            for index in range(len(user_list)) :
                
                logging.info("next user index is %s"  % index)
                
                user = user_list[index]
                post = post_list[index]
                
                logging.info("next user to is: %s" % user.user_id)
                logging.info("next post is: %s" % post.key())
                
                
                status_text = "i just mixed the post from @%s to @%s" % (post.social_user.shortcut_social_username,user.shortcut_social_username)
                logging.info(status_text)
                
                posted_to_twitter = True
                
                try:
                    
                    per_user_auth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
                    per_user_auth.set_access_token(user.access_token_key,user.access_token_secret)
                    
                    per_user_api = API(per_user_auth)
                    
                    if per_user_api.test():
                        per_user_api.update_status(status=post.text,source="twixmit")
                    else:
                        logging.error("failed to access api with user: %s" % user.user_id)
                        api.update_status(status="hey @%s i can't access your twitter feed!" % user.shortcut_social_username,source="twixmit")
                    
                except TweepError, e:
                    logging.error("TweepError: %s", e)
                    posted_to_twitter = False
                    
                mix_model = model.SocialPostMixesForUsers(origin_post=post,posted_to_user=user,posted_from_user=post.social_user,posted_to_twitter=posted_to_twitter)
                mix_model.put()
                
                if post.resubmit == True:
                    post.day_created = move_to
                    post.put()
    
    def move_small_posts_list(self,post_list,move_to):
        
        for post in post_list:
            if post.resubmit == True:
                post.day_create = move_to
                post.put
            
    
    def get(self): 
        
        auth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        auth.set_access_token(social_keys.TWITTER_APP_ACCESS_TOKEN,social_keys.TWITTER_APP_ACCESS_TOKEN_SECRET)
        
        api = API(auth)
        api_is_working = api.test()
        
        dt = datetime.datetime.fromtimestamp(time.time())
        
        logging.info("current time is: %s" % dt)
        
        one_day = datetime.timedelta(days=1)
        yesterday = dt - one_day
        #tomorrow = dt + one_day
        
        logging.info("yesterday is: %s" % yesterday)
        logging.info("today is: %s" % dt)
        
        day_filter = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, hour=0,minute=0)
        day_today = datetime.datetime(dt.year, dt.month, dt.day, hour=0,minute=0)
        
        logging.info("day filter point is: %s" % day_filter)
        logging.info("tomorrow move to point is: %s" % day_today)
        
        q = model.SocialPostsForUsers.all()
        q.filter("day_created >=",day_filter)
        
        user_list = []
        post_list = []
        
        config = db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)
        counter = 0
        for result in q.run(config=config):
            
            if counter % 1000 == 0:
                self.perform_mix(user_list,post_list,api,day_today)
                user_list = []
                post_list = []
                
            user_list.append(result.social_user)
            post_list.append(result)
            
            counter = counter + 1
        
        self.perform_mix(user_list,post_list,api,day_today)
        
        if counter < 2:
            status_text = "nobody wanted to play the twixmit today, not enough post for %s" % (day_filter)
            self.move_small_posts_list(post_list,day_today)
        else:
            status_text = "there were %s many mix ups on %s" % (counter,day_filter)
            
        logging.info(status_text)
        try:
            api.update_status(status=status_text,source="twixmit")
        except TweepError, e:
            logging.error("TweepError: %s", e)
                
        logging.info("done with mix assignments")


def main():
    application = webapp.WSGIApplication([('/tasks/dailymix/', DailyMixHandler)], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
