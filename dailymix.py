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
import helpers

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError

class DailyMixHandler(webapp.RequestHandler):
    
    def perform_demo(self,api):
        statues = memcache.get("twixmit_friends_timeline")
        if statues == None:
            statues = api.friends_timeline()
            memcache.add("twixmit_friends_timeline", statues, 60)
        
        user_list = []
        post_list = []
        
        for status in statues:
            status_text = status.text
            status_user = status.user.screen_name
            
            details_link = "https://twitter.com/%s/status/%s" % (status_user,status.id_str)
            
            combo = [status_text,status_user,details_link]
            
            logging.info("details link: %s" % details_link)
            
            user_list.append(status_user)
            post_list.append(combo)
            
        random.shuffle(user_list)
        random.shuffle(post_list)
        
        for index in range(len(user_list)):
            
            combo = post_list[index]
            to_user = user_list[index]
            
            #whats_left_for_text = 140 - (10 + len(to_user) + len(combo[1]) )
            #logging.info("whats left for text: %s" % whats_left_for_text)
            
            #if (len(combo[0]) + whats_left_for_text) > 140:
            #   trim_to = (len(combo[0]) + whats_left_for_text) - (140 + 3)
            #   logging.info("trimming text to length: %s" % trim_to)
            #   
            #   combo[0] = "%s..." % combo[0][:trim_to]
            
            status = "f: @%s %s t: @%s" % (combo[1],combo[2],to_user)
            
            logging.info(status)
            
            try:
                api.update_status(status=status,source="twixmit")
            except TweepError, e:
                logging.error("TweepError: %s", e)
        
    
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
        
        logging.info("yesterday is: %s" % yesterday)
        logging.info("today is: %s" % dt)
        
        day_filter = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, hour=0,minute=0)
        day_today = datetime.datetime(dt.year, dt.month, dt.day, hour=0,minute=0)
        
        logging.info("day filter point is: %s" % day_filter)
        logging.info("tomorrow move to point is: %s" % day_today)
        
        q = model.SocialPostsForUsers.all()
        q.filter("day_created >=",day_filter)
        
        #TODO the resubmits aren't being pulled here an need to be
        
        user_list = []
        post_list = []
        
        queries = helpers.Queries()
        query_count = q.count(limit=10)
        
        logging.info("query count limit check: %s" % query_count)
        
        if query_count > 10:
        
            counter = 0
            for result in q.run(config= queries.get_db_run_config_eventual() ):
                
                if counter % 1000 == 0:
                    self.perform_mix(user_list,post_list,api,day_today)
                    user_list = []
                    post_list = []
                    
                user_list.append(result.social_user)
                post_list.append(result)
                
                counter = counter + 1
            
            self.perform_mix(user_list,post_list,api,day_today)
            
            status_text = "there were %s mix ups on %s" % (counter,day_filter)    
            logging.info(status_text)
            
            try:
                api.update_status(status=status_text,source="twixmit")
            except TweepError, e:
                logging.error("TweepError: %s", e)
                
        else:
            status_text = "nobody wanted to play the twixmit today, running demo for %s" % (day_filter)
            
            try:
                api.update_status(status=status_text,source="twixmit")
            except TweepError, e:
                logging.error("TweepError: %s", e)
                
            self.move_small_posts_list(post_list,day_today)
            
            logging.info("running demo mode of the mix")
            self.perform_demo(api)
        
        logging.info("done with mix assignments")


def main():
    application = webapp.WSGIApplication([('/tasks/dailymix/', DailyMixHandler)], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
