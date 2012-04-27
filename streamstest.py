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

import os,logging,re,sys
import social_keys

sys.path.insert(0, 'tweepy')

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError
from tweepy.streaming import StreamListener,Stream

class TestStreamListener(StreamListener):
    def on_status(self, status):
        logging.info(status)
        return

class StreamsTestsHandler(webapp.RequestHandler):

    def get(self): 
        auth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        auth.set_access_token(social_keys.TWITTER_APP_ACCESS_TOKEN,social_keys.TWITTER_APP_ACCESS_TOKEN_SECRET)
        
        api = API(auth)
        api_is_working = api.test()
        
        listener = TestStreamListener(api=api)
        stream = Stream(auth,listener)
        stream.sample(count=10)
        
def main():
    application = webapp.WSGIApplication([('/streams/tests/', StreamsTestsHandler)], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()