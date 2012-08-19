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

IS_GAE = True

try:
    from google.appengine.ext import webapp
    from google.appengine.ext.webapp import util
    from google.appengine.api import users
    from google.appengine.ext.webapp import template
except Exception, exception:
    IS_GAE = False
    pass

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
#   http://docs.python.org/library/urllib2.html
#   http://stackoverflow.com/questions/3338853/how-to-declare-a-timeout-using-urllib2-on-google-app-engine
#   https://dev.twitter.com/docs/api/1/get/statuses/show/%3Aid
#   https://dev.twitter.com/docs/streaming-api/methods

class TestStreamListener(StreamListener):
    def on_status(self, status):
        print status.user.screen_name,status.text
        return
        
    def on_error(self, status_code):
        logging.error(status_code)
        return False # Don't kill the stream

    def on_timeout(self):
        #print >> sys.stderr, 'Timeout...'
        logging.error('Timeout...')
        return True # Don't kill the stream

class StreamsTestsPlain(object):
    
    def __init__(self):
        self._stream = None
        self._oauth = None
        self._oauth_api = None
        
        self._stream_init()
        self._oauth_init()
        
    def _oauth_init(self):
        self._oauth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        self._oauth.set_access_token(social_keys.TWITTER_APP_ACCESS_TOKEN,social_keys.TWITTER_APP_ACCESS_TOKEN_SECRET)
        self._oauth_api = API(self._oauth)
    
    def _stream_init(self):
        api1 = API()
        
        headers = {}
        headers["Accept-Encoding"] = "deflate, gzip"
        stream_auth = BasicAuthHandler(social_keys.TWITTER_HTTP_AUTH_U,social_keys.TWITTER_HTTP_AUTH_P)
        
        l = TestStreamListener(api=api1)
        self._stream = Stream(auth=stream_auth,listener=l,secure=True,headers=headers)
    
    def sample(self):
        self._stream.sample()
        
    def filter_follow(self):
        follow_names = ['hnfirehose','StockTwits','YahooFinance','Street_Insider','TheStreet','SquawkCNBC','CNBC','AP_PersonalFin','themotleyfool','MarketWatch','Reuters_Biz']
        follow_usr_objs = self._oauth_api.lookup_users(screen_names=follow_names)
        follow_ids = []
        
        for follow_usr in follow_usr_objs:
            follow_ids.append(follow_usr.id)
        
        print follow_ids
        
        self._stream.filter(follow=follow_ids)
    
    def filter(self):
        self._stream.filter(track=["@newsdotme","@twixmit","@app_engine"])

if IS_GAE:
    class StreamsTestsHandler(webapp.RequestHandler):   
        def get(self): 
            pass
    
def main():  
    if IS_GAE:  
        application = webapp.WSGIApplication([('/streams/tests/', StreamsTestsHandler)], debug=True)
        util.run_wsgi_app(application)
    else:
        try:
            r = StreamsTestsPlain()
            r.filter()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()