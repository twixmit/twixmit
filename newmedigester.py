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
    from google.appengine.runtime import DeadlineExceededError
    from google.appengine.ext import db
    
    class NewsMeDigestionStoryModel(db.Model):
        digest_story_title = db.TextProperty(required=True)
        digest_story_link = db.StringProperty(required=True)
        digest_user = db.StringProperty(required=True)
        created = db.DateTimeProperty(auto_now_add=True)
        updated = db.DateTimeProperty(auto_now=True)
        
    class NewsMeDigestionStoryModelQueries(object):
    
        def get_last_created_article_user(self):
            # SELECT * FROM NewsMeDigestionStoryModel order by created desc limit 1
            q = NewsMeDigestionStoryModel.all()
            q.order("-created")
            
            config = db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)
            results = q.fetch(1, config=config )
            
            last_created_article_user = None
            
            for r in results: 
                last_created_article_user = r.digest_user
                
            return last_created_article_user
    
except Exception, exception:
    #logging.error(exception)
    #raise exception
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
        conn = httplib.HTTPConnection(self._host,timeout=4)
        next_url = self._url % (self._host,self._starting_user)
        
        logging.info("next url: %s" % next_url)
        
        conn.connect()
        conn.request('GET',  next_url)
        
        resp = None
        
        try:
            resp = conn.getresponse()
        except Exception, exception:
            logging.error(exception)
        
        if resp == None:
            logging.error("http connection response timeout for url: %s" % (next_url))
            return None
        elif resp.status != 200:
            logging.error("http connection response code is not 200 for url: %s,%i" % (next_url,resp.status))
            return None
        else:
            return resp.read()
            
class NewsMeDigestTweeter(object):
    def __init__(self,debug=True):
        self._oauth = None
        self._oauth_api = None
        
        self._oauth_init()
        self._debug = debug
        
        self.tweet_counter = 0
    
    def _oauth_init(self):
        self._oauth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        self._oauth.set_access_token(social_keys.TWITTER_APP_ACCESS_TOKEN,social_keys.TWITTER_APP_ACCESS_TOKEN_SECRET)
        self._oauth_api = API(self._oauth)
    
    def follow_digestion_user(self,digestion_user):
        try:
            friend = self._oauth_api.create_friendship(digestion_user)
        except TweepError, e:
            logging.error("TweepError: %s", e)
        
        logging.info("following: %s" % digestion_user)
    
    def tweet_from_digestion(self,digest_articles, digestion_user):
        
        for k, v in digest_articles.iteritems():
            
            status_text = "%s %s" % (v,k)
            
            model_check = self.check_model_for_tweet(digestion_user,k)
            
            logging.info("model check for user and link is %s" % model_check)
            
            if not self._debug and not model_check:
                try:
                    self._oauth_api.update_status(status=status_text,source="twixmit")
                    self.tweet_counter = self.tweet_counter + 1
                except TweepError, e:
                    logging.error("TweepError: %s", e)
            
            
            if not model_check:
                self.save_tweet_to_model(digestion_user,k,v)
            else:
                logging.warn("link was already tweeted: %s" % k)
                
    
    def check_model_for_tweet(self,user,link):
        logging.info("checking model for link and user: %s, %s" % (link,user) )
        if IS_GAE:
            try:
                q = NewsMeDigestionStoryModel.all()
                q.filter("digest_story_link =",link )
                config = db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)
                results = q.fetch(1, config=config )
                
                for r in results:
                    logging.warn("model contains link: %s" % (link) )
                    return True
                     
                logging.info("model does not contain link and user: %s, %s" % (link,user) )
                return False
                
            except Exception, exception:
                logging.error(exception)
                return False
        else:
            logging.info("not IS_GAE, checking model for link and user: %s, %s" % (link,user) )
            return False 
    
    def save_tweet_to_model(self,user,link,title):
        if IS_GAE:
            try:
                newsme_model = NewsMeDigestionStoryModel(digest_story_link=link,digest_story_title=title,digest_user=user)
                newsme_model.put()
            except Exception, exception:
                logging.error("failed to save date to model: %s, %s" % (user,link))
                logging.error(exception)
        else:
            pass 


def run_digestion():

    last_user_as_seed = None

    if IS_GAE:
        newsMeQueries = NewsMeDigestionStoryModelQueries()
        last_user_as_seed = newsMeQueries.get_last_created_article_user()
    
    logging.info("last user as see is: %s" % last_user_as_seed )
    
    if last_user_as_seed == None:
        digester = NewsMeDigester(crawl_depth=20)
    else:
        digester = NewsMeDigester(digest_explore_seeds=["/%s" % last_user_as_seed],crawl_depth=20)
    
    # we dont tweet while we test, True = No Tweet, False = Tweet
    tweeter = NewsMeDigestTweeter(debug=False)
    
    while digester.next():
        digester.do_digest_digestion()
        tweeter.tweet_from_digestion(digester.get_parser_digest_articles(), digester.get_current_user() )
        tweeter.follow_digestion_user(digester.get_current_user() )
        logging.info("tweet counter: %i" % tweeter.tweet_counter)
        

if IS_GAE:
    class NewsmeDigestionDeleteHandler(webapp.RequestHandler):
         def get(self): 
            q = NewsMeDigestionStoryModel.all()
            results = q.fetch(1000)
        
            for r in results:
                logging.info("deleting demo entity: %s" % r.key)
                r.delete()
    
    class NewsmeDigestionHandler(webapp.RequestHandler):
        def get(self): 
            try:
                run_digestion()
            except DeadlineExceededError:
                self.response.clear()
                self.response.set_status(500)
                self.response.out.write("This operation could not be completed in time: DeadlineExceededError")
            
    application = webapp.WSGIApplication( \
        [('/tasks/newsmedigestion/', NewsmeDigestionHandler),\
        ('/tasks/newsmedigestiondelete/',NewsmeDigestionDeleteHandler)], \
        debug=True)

def main():
    if IS_GAE:
        util.run_wsgi_app(application)
    else: 
        run_digestion()
    
if __name__ == '__main__':
    main()