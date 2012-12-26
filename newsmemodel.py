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


from google.appengine.ext import db

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

    def get_oldest_link_date(self):
        q = db.GqlQuery("SELECT created FROM NewsMeDigestionStoryModel ORDER BY created ASC LIMIT 1")
        results = q.get(config=self._db_run_config )
        return results.created
    
    def get_articles_between(self,start,stop):
        q = NewsMeDigestionStoryModel.all()
        q.filter("created >= ",start)
        q.filter("created <= ",stop)
        q.order("-created")
        
        results = q.fetch(limit=1000,config=self._db_run_config)
        
        return results
        
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