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
from tweepy.auth import BasicAuthHandler

# Reference: https://gist.github.com/1112928
#   http://mtrovo.com/blog/2011/07/using-the-twitter-streaming-api-with-python-and-tweepy/
#   http://code.google.com/p/googleappengine/source/browse/trunk/python/google/appengine/dist27/httplib.py

class TestStreamListener(StreamListener):
    def on_status(self, status):
        logging.info(status.text)
        return
        
    def on_error(self, status_code):
        logging.error(status_code)
        return False # Don't kill the stream

    def on_timeout(self):
        #print >> sys.stderr, 'Timeout...'
        logging.error('Timeout...')
        return True # Don't kill the stream

class StreamsTestsHandler(webapp.RequestHandler):

    def get(self): 
        #auth1 = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        #auth1.set_access_token(social_keys.TWITTER_APP_ACCESS_TOKEN,social_keys.TWITTER_APP_ACCESS_TOKEN_SECRET)
        
        api1 = API()
        
        #headers = {}
        #headers["Authorization"] = "Basic %s" % social_keys.TWITTER_HTTP_AUTH_BASE64
        stream_auth = BasicAuthHandler(social_keys.TWITTER_HTTP_AUTH_U,social_keys.TWITTER_HTTP_AUTH_P)
        
        l = TestStreamListener(api=api1)
        stream = Stream(auth=stream_auth,listener=l,secure=True)
        
        #setTerms = ['hello', 'goodbye', 'goodnight', 'good morning']
        stream.sample()
        #stream.retweet()
        #stream.filter(None,setTerms)
    
application = webapp.WSGIApplication([('/streams/tests/', StreamsTestsHandler)], debug=True)
    
def main():    
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()