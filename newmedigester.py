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
import urllib2
import sys
import social_keys

sys.path.insert(0, 'tweepy')

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError

#class NewsMeHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
#    http_error_301 = http_error_303 = http_error_307 = http_error_302
#    
#    def http_error_302(self, req, fp, code, msg, headers):
#        print "Cookie Manip Right Here"
#        return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)

class NewsMeDigestParser(HTMLParser):    
    def __init__(self):
        #div#id="digest-date", date="May 01, 2012"
        self._digest_date = None 
        #a.class="story-link", data-ga-event-action="Top Stories", href=<link>, data=<link title>
        self._digest_articles = []
        #a.class="explore-digest-link" href=/<user>
        self._digest_explore_users = []
        
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
                    print "digest story link found:", href_in_attrs.strip()
                    self._digest_explore_users.append(href_in_attrs.strip())
                    explore_digest_link_found = False
                elif store_link_found == True:
                    self.handle_start_tag_attr_story_link(href_in_attrs)
                    store_link_found = False
        
            if tag == 'div' and attr[0] == 'id' and attr[1] == 'digest-date':
                print "digest date:",attr, type(attr)  
                self._tag_states["_digest_date"] = True
            
            # explore digest links
            elif tag == 'a' and attr[0] == 'class' and attr[1] == 'explore-digest-link' and href_in_attrs == None:
                explore_digest_link_found = True
            elif tag == 'a' and attr[0] == 'class' and attr[1] == 'explore-digest-link' and href_in_attrs != None:
                print "digest explore user found:", href_in_attrs.strip()
                self._digest_explore_users.append(href_in_attrs.strip())
                explore_digest_link_found = False
            
            # story links
            elif tag == 'a' and attr[0] == 'class' and attr[1] == 'story-link' and href_in_attrs != None:
                self.handle_start_tag_attr_story_link(href_in_attrs)
                store_link_found = False
            
        href_in_attrs = None
    
    def handle_start_tag_attr_story_link(self,href_in_attrs):
        print "digest story link found:", href_in_attrs.strip()
        rec = [href_in_attrs.strip(),None]
        self._digest_articles.append(rec)
        self._tag_states["_digest_articles"] = True
        
    def story_link_fetch(self,story_link):
        #opener = urllib2.build_opener(NewsMeHTTPRedirectHandler)
        #TODO for following the news me tracking redirect to source page
        #<link rel="shortlink" href="http://blog.yottaa.com/?p=3233">
        #http://code.google.com/p/shortlink/wiki/Specification
        pass
    
    def handle_endtag(self, tag): pass
        
    def handle_data(self, data):
        if self._tag_states["_digest_date"] == True and self._digest_date == None:
            print "digest date data:",data.strip()
            self._digest_date = data.strip()
            self._tag_states["_digest_date"] == False
        elif self._tag_states["_digest_articles"] == True:
            print "digest story link date:",data.strip()
            self._digest_articles[-1][1] = data.strip()
            self._tag_states["_digest_articles"] = False
            
            
class NewsMeDigester(object):
    def __init__(self,starting_user="tepietrondi",crawl_depth=1):
        self._starting_user = starting_user
        self._crawl_depth_limit=crawl_depth
        self._crawl_depth_counter = 0
        self._host = "www.news.me"
        self._url = "http://%s/%s"
        self._parser = None
        
    def do_digest_digestion(self):
        digest_data = self.get_digest_page()
        self._parser = NewsMeDigestParser()
        if digest_data != None:
            self._parser.feed(digest_data)
    
    def get_parser_digest_articles(self):
        return self._parser.get_digest_articles()
                
    def get_digest_page(self):
        conn = httplib.HTTPConnection(self._host)
        conn.connect()
        conn.request('GET', self._url % (self._host,self._starting_user) )
        resp = conn.getresponse()
        if resp.status != 200:
            return None
        else:
            return resp.read()
            
class NewsMeDigestTweeter(object):
    def __init__(self):
        self._oauth = None
        self._oauth_api = None
        
        self._oauth_init()
    
    def _oauth_init(self):
        self._oauth = OAuthHandler(social_keys.TWITTER_CONSUMER_KEY, social_keys.TWITTER_CONSUMER_SECRET)
        self._oauth.set_access_token(social_keys.TWITTER_APP_ACCESS_TOKEN,social_keys.TWITTER_APP_ACCESS_TOKEN_SECRET)
        self._oauth_api = API(self._oauth)
    
    def tweet_from_digestion(self,digest_articles):
        
        for article in digest_articles:
            status = "%s %s" % (article[1],article[0])
            print status
            
            #try:
            #    self._oauth_api.update_status(status=status_text,source="twixmit")
            #except TweepError, e:
            #    logging.error("TweepError: %s", e)

def main():
    digester = NewsMeDigester()
    digester.do_digest_digestion()
    
    tweeter = NewsMeDigestTweeter()
    tweeter.tweet_from_digestion(digester.get_parser_digest_articles())
    
    
if __name__ == '__main__':
    main()