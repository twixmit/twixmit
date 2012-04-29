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
#   

class TestStreamListener(StreamListener):
    def on_status(self, status):
        print status.text
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
        self._stream_init()
    
    def _stream_init(self):
        api1 = API()
        
        headers = {}
        headers["Accept-Encoding"] = "deflate, gzip"
        stream_auth = BasicAuthHandler(social_keys.TWITTER_HTTP_AUTH_U,social_keys.TWITTER_HTTP_AUTH_P)
        
        l = TestStreamListener(api=api1)
        self._stream = Stream(auth=stream_auth,listener=l,secure=True,headers=headers)
        
    def sample(self):
        self._stream.sample()
        
    def filter(self):
        self._stream.filter(track=["$AKAM","$EMC","$AMZN","$AAPL","@StockTwits"])

if IS_GAE:
    class StreamsTestsHandler(webapp.RequestHandler):
    
        def get(self): 
            plain = StreamsTestsPlain()
            plain.stream()
    
def main():  
    if IS_GAE:  
        application = webapp.WSGIApplication([('/streams/tests/', StreamsTestsHandler)], debug=True)
        util.run_wsgi_app(application)
    else:
        r = StreamsTestsPlain()
        r.filter()

if __name__ == '__main__':
    main()