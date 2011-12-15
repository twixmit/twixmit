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
        
        day_filter = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, hour=0,minute=0)
        
        logging.info("day filter point is: %s" % day_filter)
        
        q = model.SocialPostsForUsers.all()
        q.filter("day_created =",day_filter)
        
        user_list = []
        post_list = []
        
        config = db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)
        for result in q.run(config=config):
            user_list.append(result.social_user)
            post_list.append(result)
        
        logging.info("list sized for users and posts are: %s" % len(user_list))
        
        random.shuffle(user_list)
        random.shuffle(post_list)
        
        for index in range(len(user_list)) :
            user = user_list[index]
            post = post_list[index]
            
            logging.info("next user to is: %s" % user.user_id)
            logging.info("next post is: %s" % post.key())
            
            mix_model = model.SocialPostMixesForUsers(origin_post=post,posted_to_user=user,posted_from_user=post.social_user,posted_to_twitter=False)
            mix_model.put()
            
            api.update_status(status=post.text,source="twixmit")
            

def main():
    application = webapp.WSGIApplication([('/tasks/dailymix/', DailyMixHandler)], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
