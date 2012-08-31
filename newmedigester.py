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

IS_DEBUG = False

from HTMLParser import HTMLParser
import httplib
import urllib2,urllib
import sys
import social_keys
import logging
import os
import helpers
import cache_keys

sys.path.insert(0, 'tweepy')

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.runtime import DeadlineExceededError
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import memcache

class NewsMeDigestionStoryModel(db.Model):
    digest_story_title = db.TextProperty(required=True)
    digest_story_link = db.StringProperty(required=True)
    digest_user = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
class NewsMeDigestionSeedUsers(db.Model):
    seeds = db.StringListProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
class NewsMeModelQueries(object):
    
    def __init__(self):
        self._db_run_config = self._get_db_run_config_eventual()
    
    def _get_db_run_config_eventual(self):
        # https://developers.google.com/appengine/docs/python/datastore/queries?hl=en#Data_Consistency
        return db.create_config(deadline=10, read_policy=db.EVENTUAL_CONSISTENCY)

    def get_many_articles(self,how_many=20):
        q = NewsMeDigestionStoryModel.all()
        q.order("-created")
        
        results = q.fetch(how_many,config=self._db_run_config)
        
        return results

    #def get_many_article_users(self,how_many=20):
    #    q = db.GqlQuery("SELECT digest_user FROM NewsMeDigestionStoryModel ORDER BY CREATED DESC")
    #    
    #    results = q.fetch(how_many, config=self._db_run_config )
    #    
    #    article_users = []
    #    
    #    for r in results: 
    #        #logging.info("next user: %s" % (r.digest_user) )
    #        article_users.append("/%s" % r.digest_user) 
    #        
    #    return list(set(article_users))
        
    def check_model_for_tweet(self,user,link):
        logging.info("checking model for link and user: %s, %s" % (link,user) )
        try:
            #q = NewsMeDigestionStoryModel.all()
            #q.filter("digest_story_link =",link )
            
            q = db.GqlQuery("SELECT __key__ FROM NewsMeDigestionStoryModel WHERE digest_story_link = :1", link)
            
            results = q.get(config=self._db_run_config )
            
            if results == None:
                logging.info("model does not contain link and user: %s, %s" % (link,user) )
                return False
            else:
                logging.warn("model contains link: %s" % (link) )
                return True
                 
        except Exception, exception:
            logging.error(exception)
            return False
    

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
            logging.info("raw href in attr: %s" % href_in_attrs)
            rec = urllib.unquote(href_in_attrs.strip().split("url=")[1].split("&")[0])
            logging.info("extracted link: %s" % rec)
        except IndexError,e:
            logging.error("index error on raw href in attr: %s" % href_in_attrs.strip())
            rec = href_in_attrs.strip()
            
        #rec = rec.rsplit("?")[0]
        #logging.info("removed url junk link: %s" % rec)
        
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
            

class NewsMeSeeder(object):
    
    def __init__(self):
        self._static_known_seeds = ["/timoreilly","/twixmit","/tepietrondi","/lastgreatthing","/Borthwick","/anildash","/myoung","/davemorin","/innonate","/ejacqui"]
        
    def init_seed_model(self):
        q = NewsMeDigestionSeedUsers.all()
            
        config = db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)
        result_count = q.count(config=config)
        
        if result_count == 0:
            try:
                seed_model = NewsMeDigestionSeedUsers(seeds=self._static_known_seeds)
                seed_model.put()
            except Exception, exception:
                # ERROR    2012-06-02 15:07:56,629 newmedigester.py:321] 'ascii' codec can't decode byte 0xe2 in position 7: ordinal not in range(128)
                logging.error("failed to save static seeds to model: %s" % (self._static_known_seeds))
                logging.error(exception)
                
    def get_seeds(self):
        q = NewsMeDigestionSeedUsers.all()
        
        config = db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)
        results = q.get(config=config)
        
        return results.seeds
    
    def add_to_seeds(self,seed):
        q = NewsMeDigestionSeedUsers.all()
        
        config = db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)
        results = q.get(config=config)
        
        results.seeds.append(seed)
        results.seeds = list(set(p.seeds))
        results.put()
            
    def force_set_seeds(self,seeds):
        
        logging.info("passed seeds: %s" % seeds)
        
        q = NewsMeDigestionSeedUsers.all()
        
        config = db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)
        results = q.get(config=config)
                   
        logging.info("result seeds: %s" % results.seeds)
        
        results.seeds = seeds
        results.put()
        
            
class NewsMeDigester(object):
    def __init__(self,digest_explore_seeds=["/twixmit"],crawl_depth=1):
        self._starting_user = None
        self._crawl_depth_limit=crawl_depth
        self._crawl_depth_counter = 0
        self._host = "www.news.me"
        self._url = "http://%s/%s"
        
        self._digested_users = {}
        self._digest_articles = {}
        self._digest_explore_users = digest_explore_seeds
        # self._utils = helpers.Util()
        
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
    
        cached_html_response_key = cache_keys.NEWSME_DIGESTPAGE_HTML % self._starting_user
        cached_html_response_value = memcache.get(cached_html_response_key)
        
        if cached_html_response_value == None:
    
            conn = httplib.HTTPConnection(self._host,timeout=4)
            next_url = self._url % (self._host,self._starting_user)
            
            logging.info("next url: %s" % next_url)
            
            #TODO be a better crawler
            headers = {'User-Agent' : 'twixmitbot' }
            
            conn.connect()
            conn.request('GET',  next_url, headers)
            
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
                response_read =  resp.read()
                # memecache_digest_response = self._util.get_time_left_in_day().seconds
                # logging.info("memecache_digest_response = %s" % memecache_digest_response)
                memcache.add(cached_html_response_key, response_read, cache_keys.NEWSME_CACHE_DIGEST_RESPONSE )
                return response_read
        else:
            return cached_html_response_value
            
class NewsMeDigestTweeter(object):
    def __init__(self,debug=True):
        self._oauth = None
        self._oauth_api = None
        
        self._oauth_init()
        self._debug = debug
        
        self.tweet_counter = 0
        
        self._model_queries = NewsMeModelQueries()
    
    def _oauth_init(self):
        self._oauth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        self._oauth.set_access_token(social_keys.TWITTER_APP_ACCESS_TOKEN,social_keys.TWITTER_APP_ACCESS_TOKEN_SECRET)
        self._oauth_api = API(self._oauth)
    
    def follow_digestion_user(self,digestion_user):
        try:
            if self._oauth_api.exists_friendship(digestion_user, 'twixmit') == False:
                friend = self._oauth_api.create_friendship(digestion_user)
        except TweepError, e:
            logging.error("TweepError: %s", e)
        
        logging.info("following: %s" % digestion_user)
    
    def tweet_from_digestion(self,digest_articles, digestion_user):
        
        for k, v in digest_articles.iteritems():
            
            status_text = "%s %s" % (v,k)
            
            model_check = self._model_queries.check_model_for_tweet(digestion_user,k)
            
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
                    
    
    def save_tweet_to_model(self,user,link,title):
        try:
            title = unicode(title, errors='replace')
            newsme_model = NewsMeDigestionStoryModel(digest_story_link=link,digest_story_title=title,digest_user=user)
            newsme_model.put()
        except Exception, exception:
            # ERROR    2012-06-02 15:07:56,629 newmedigester.py:321] 'ascii' codec can't decode byte 0xe2 in position 7: ordinal not in range(128)
            logging.error("failed to save date to model: %s, %s" % (user,link))
            logging.error(exception)
        

class NewsmeDigestionDeleteHandler(webapp.RequestHandler):
     def get(self): 
        model_queries = NewsMeModelQueries()
        results = model_queries.get_many_articles(1000)
    
        for r in results:
            logging.info("deleting demo entity: %s" % r.key)
            r.delete()

class NewsmeDigestionAddSeedHandler(webapp.RequestHandler):
     def get(self): 
        
        seeder = NewsMeSeeder()
        seeder.init_seed_model()
        
        who = self.request.get("who")
        seeder.add_to_seeds(who)

class NewsmeDigestionReportHandler(webapp.RequestHandler):
    def get(self):
        _path = os.path.join(os.path.dirname(__file__), 'newsmereport.html')
        
        util = helpers.Util()
        seconds_to_cache = util.get_report_http_time_left()
        
        cache_results = memcache.get(cache_keys.NEWSME_REPORTHANDLER_ALL_STORIES)
        
        if cache_results == None:
            model_queries = NewsMeModelQueries()
            results = model_queries.get_many_articles(100)
            
            memcache.add(cache_keys.NEWSME_REPORTHANDLER_ALL_STORIES, results, seconds_to_cache)
            
        else:
            results = cache_results
        
        _template_values = {}
        _template_values["links"] = results
        
        
        self.response.headers["Expires"] = util.get_expiration_stamp(seconds_to_cache)
        self.response.headers["Cache-Control: max-age"] = seconds_to_cache
        self.response.headers["Cache-Control"] = "public"
        
        self.response.out.write(template.render(_path, _template_values))
    

class NewsmeDigestionHandler(webapp.RequestHandler):
    def run_digestion(self):
        last_user_as_seed = None
        
        seeder = NewsMeSeeder()
        seeder.init_seed_model()
        
        digest_explore_seeds = seeder.get_seeds()
        
        #newsMeQueries = NewsMeModelQueries()
        #last_users_as_seed = newsMeQueries.get_many_article_users(how_many=500)
        
        #logging.info("last_users_as_seed=%s" % last_users_as_seed)
        logging.info("digest_explore_seeds=%s" % digest_explore_seeds)
        
        #if last_users_as_seed == None:
        #    last_users_as_seed = []
        
        #if not digest_explore_seeds == None:
        #    last_users_as_seed.extend(digest_explore_seeds)
        #else:
        #    logging.warn("digest_explore_seeds is None, this should never happen!")
        
        #logging.info("last_users_as_seed=%s" % last_users_as_seed)
        
        #last_users_as_seed = list(set(last_users_as_seed))
        
        #logging.info("last_users_as_seed=%s" % last_users_as_seed)
        
        #seeder.force_set_seeds(last_users_as_seed)
        
        digester = NewsMeDigester(digest_explore_seeds=digest_explore_seeds,crawl_depth=10)
        
        # we dont tweet while we test, True = No Tweet, False = Tweet
        tweeter = NewsMeDigestTweeter(debug=IS_DEBUG)
        
        while digester.next():
            digester.do_digest_digestion()
            tweeter.tweet_from_digestion(digester.get_parser_digest_articles(), digester.get_current_user() )
            tweeter.follow_digestion_user(digester.get_current_user() )
            logging.info("tweet counter: %i" % tweeter.tweet_counter)
    
    def get(self): 
        try:
            self.run_digestion()
        except DeadlineExceededError:
            self.response.clear()
            self.response.set_status(500)
            self.response.out.write("This operation could not be completed in time: DeadlineExceededError")
        
application = webapp.WSGIApplication( \
    [('/tasks/newsmedigestion/', NewsmeDigestionHandler),\
    ('/tasks/newsmedigestiondelete/',NewsmeDigestionDeleteHandler), \
    ('/tasks/newsmedigestionaddseed/',NewsmeDigestionAddSeedHandler), \
    ('/newsme/digestreport/',NewsmeDigestionReportHandler), \
    ('/',NewsmeDigestionReportHandler)], \
    debug=True)

def main():
    util.run_wsgi_app(application)
    
if __name__ == '__main__':
    main()