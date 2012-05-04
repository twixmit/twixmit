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

from HTMLParser import HTMLParser
import httplib
import urllib2,urllib
import sys
import social_keys
import logging

sys.path.insert(0, 'tweepy')

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError

IS_GAE = True
try:
    from google.appengine.ext import webapp
    from google.appengine.ext.webapp import util
    #from google.appengine.ext import db
    
    #class NewsMeDigestionStory(db.Model):
    #    digest_story_link = db.Link(required=True)
    #    digest_story_title = db.StringProperty(required=True)
    #    digest_user = db.StringProperty(required=True)
    #    digest_date_string = db.StringProperty(required=True)
    #    created = db.DateTimeProperty(auto_now_add=True)
    #    updated = db.DateTimeProperty(auto_now=True)
    
except Exception, exception:
    logging.getLogger().setLevel("INFO")
    IS_GAE = False 

# Digest HTML from user 
# Generate map of articles and list of other users to explore
class NewsMeDigestParser(HTMLParser):    
    def __init__(self):
        #div#id="digest-date", date="May 01, 2012"
        self._digest_date = None 
        #a.class="story-link", data-ga-event-action="Top Stories", href=<link>, data=<link title>
        self._digest_articles = {}
        #a.class="explore-digest-link" href=/<user>
        self._digest_explore_users = {}
        
        self._tag_states = {"_digest_date" :False, "_digest_articles" : False, "_digest_explore_users" : False}
        
        #http://stackoverflow.com/questions/9698614/super-raises-typeerror-must-be-type-not-classobj-for-new-style-class
        HTMLParser.__init__(self)
    
    def get_digest_articles(self):
        return self._digest_articles
    
    def get_digest_explore_users(self):
        return self._digest_explore_users
    
    def handle_starttag(self, tag, attrs):
        
        href_in_attrs = None
        explore_digest_link_found = False
        store_link_found = False
                
        for attr in attrs:
            if tag == 'a' and attr[0] == 'href':
                href_in_attrs = attr[1]
                
                if explore_digest_link_found == True:
                    #print "digest story link found:", href_in_attrs.strip()
                    self._digest_explore_users[href_in_attrs.strip()] = True
                    explore_digest_link_found = False
                elif store_link_found == True:
                    self.handle_start_tag_attr_story_link(href_in_attrs)
                    store_link_found = False
        
            if tag == 'div' and attr[0] == 'id' and attr[1] == 'digest-date':
                #print "digest date:",attr, type(attr)  
                self._tag_states["_digest_date"] = True
            
            # explore digest links
            elif tag == 'a' and attr[0] == 'class' and attr[1] == 'explore-digest-link' and href_in_attrs == None:
                explore_digest_link_found = True
            elif tag == 'a' and attr[0] == 'class' and attr[1] == 'explore-digest-link' and href_in_attrs != None:
                #print "digest explore user found:", href_in_attrs.strip()
                self._digest_explore_users[href_in_attrs.strip()] = True
                explore_digest_link_found = False
            
            # story links
            elif tag == 'a' and attr[0] == 'class' and attr[1] == 'story-link' and href_in_attrs != None:
                self.handle_start_tag_attr_story_link(href_in_attrs)
                store_link_found = False
            
        href_in_attrs = None
    
    def handle_start_tag_attr_story_link(self,href_in_attrs):
        try:
            rec = urllib.unquote(href_in_attrs.strip().split("url=")[1].split("&")[0])
        except IndexError,e:
            logging.error(href_in_attrs.strip())
            #raise e
            rec = href_in_attrs.strip()
            
        #print rec
        if not self._digest_articles.has_key(rec):
            self._digest_articles[rec] = None
            self._tag_states["_digest_articles"] = rec
        else:
            logging.warn("rec already in list: %s" % rec[0])
        
    def story_link_fetch(self,story_link):
        #opener = urllib2.build_opener(NewsMeHTTPRedirectHandler)
        #TODO for following the news me tracking redirect to source page
        #<link rel="shortlink" href="http://blog.yottaa.com/?p=3233">
        #http://code.google.com/p/shortlink/wiki/Specification
        pass
    
    def handle_endtag(self, tag): pass
        
    def handle_data(self, data):
        if self._tag_states["_digest_date"] == True and self._digest_date == None:
            #print "digest date data:",data.strip()
            self._digest_date = data.strip()
            self._tag_states["_digest_date"] == False
        elif not self._tag_states["_digest_articles"] == False:
            #print "digest story link date:",data.strip()
            self._digest_articles[self._tag_states["_digest_articles"]] = data.strip()
            self._tag_states["_digest_articles"] = False
            
            
class NewsMeDigester(object):
    def __init__(self,digest_explore_seeds=["/timoreilly","/twixmit","/tepietrondi"],crawl_depth=1):
        self._starting_user = None
        self._crawl_depth_limit=crawl_depth
        self._crawl_depth_counter = 0
        self._host = "www.news.me"
        self._url = "http://%s/%s"
        
        self._digested_users = {}
        self._digest_articles = {}
        self._digest_explore_users = digest_explore_seeds
    
    def get_current_user(self):
        return self._starting_user
    
    def next(self):
        
        if len(self._digest_explore_users ) > 0 and self._crawl_depth_counter < self._crawl_depth_limit:
            self._starting_user = self._digest_explore_users.pop(0)[1:]
            
            logging.info("starting user: %s" % self._starting_user)
            
            if self._starting_user in self._digested_users:
                logging.warn("starting is digested: %s" % self._starting_user)
                return self.next() 
            else:    
                return True
        else:
            self._starting_user = None
            return False
        
    def do_digest_digestion(self):
        digest_data = self.get_digest_page()
        parser = NewsMeDigestParser()
        if digest_data != None:
            parser.feed(digest_data)
            self._digest_explore_users.extend( parser.get_digest_explore_users().keys() )
            self._digest_articles = parser.get_digest_articles()
            self._crawl_depth_counter = self._crawl_depth_counter + 1
        else:
            logging.warn("digest data is none for: %s" % self._starting_user)
        
        
        logging.info( "self._crawl_depth_counter: %s" % self._crawl_depth_counter)
        logging.info("self._digested_users: %s" % self._digested_users)
        
        self._digested_users[self._starting_user] = True
    
    def get_parser_digest_articles(self):
        return self._digest_articles
                
    def get_digest_page(self):
        conn = httplib.HTTPConnection(self._host,timeout=5)
        next_url = self._url % (self._host,self._starting_user)
        
        logging.info("next url: %s" % next_url)
        
        conn.connect()
        conn.request('GET',  next_url)
        resp = conn.getresponse()
        
        if resp.status != 200:
            logging.error("http connection response code is not 200 for url: %s,%i" % (next_url,resp.status))
            return None
        else:
            return resp.read()
            
class NewsMeDigestTweeter(object):
    def __init__(self,debug=True):
        self._oauth = None
        self._oauth_api = None
        
        self._oauth_init()
        self._tweeted_articles = {}
        self._debug = debug
    
    def _oauth_init(self):
        self._oauth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        self._oauth.set_access_token(social_keys.TWITTER_APP_ACCESS_TOKEN,social_keys.TWITTER_APP_ACCESS_TOKEN_SECRET)
        self._oauth_api = API(self._oauth)
    
    def follow_digestion_user(self,digestion_user):
        
        status_text = "posting @%s digest articles from @newsdotme" % digestion_user
        
        if not self._debug:
            try:
                friend = self._oauth_api.create_friendship(digestion_user)
                self._oauth_api.update_status(status=status_text,source="twixmit")
            except TweepError, e:
                logging.error("TweepError: %s", e)
        
        
        logging.info(status_text)
        logging.info("following: %s" % digestion_user)
    
    def tweet_from_digestion(self,digest_articles):
        
        for k, v in digest_articles.iteritems():
            
            if not self._tweeted_articles.has_key(k):
                status_text = "%s %s" % (v,k)
                
                if not self._debug:
                    try:
                        self._oauth_api.update_status(status=status_text,source="twixmit")
                    except TweepError, e:
                        logging.error("TweepError: %s", e)
                
                logging.info(status_text)
                self._tweeted_articles[k] = v
            else:
                logging.warn("skipping article: %s" % k )


def run_digestion():
    tweet_counter = 0
    digester = NewsMeDigester(crawl_depth=10)
    # we dont tweet while we test
    tweeter = NewsMeDigestTweeter(debug=False)
    
    while digester.next():
        digester.do_digest_digestion()
        tweeter.tweet_from_digestion(digester.get_parser_digest_articles())
        tweeter.follow_digestion_user(digester.get_current_user() )
        tweet_counter = tweet_counter + 1
        logging.info("tweet counter: %i" % tweet_counter)
        

if IS_GAE:
    class NewsmeDigestionHandler(webapp.RequestHandler):
        def get(self): 
            try:
                run_digestion()
            except DeadlineExceededError:
                self.response.clear()
                self.response.set_status(500)
                self.response.out.write("This operation could not be completed in time...")
            
    application = webapp.WSGIApplication([('/tasks/newsmedigestion/', NewsmeDigestionHandler)], debug=True)

def main():
    if IS_GAE:
        util.run_wsgi_app(application)
    else: 
        run_digestion()
    
if __name__ == '__main__':
    main()