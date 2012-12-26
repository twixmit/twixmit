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


import logging
import os
import helpers
import cache_keys
import sys
import newsmemodel

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.runtime import DeadlineExceededError
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import memcache

class NewsmeDigestionSitemap(webapp.RequestHandler):
    def get(self):
        model_queries = newsmemodel.NewsMeModelQueries()
        oldest_date = model_queries.get_oldest_link_date()
        
        logging.info("oldest_date = %s" % oldest_date)
        
        util = helpers.Util()
        today_start = util.get_todays_start()
        
        logging.info("today_start = %s" % today_start)
        
        links = []
        
        request_host = self.request.headers["Host"]
        
        while oldest_date < today_start:
            template_date = oldest_date.strftime("%Y-%m-%d")
        
            next_link = "http://%s/?when=%s" % (request_host, template_date)
            
            logging.info("next_link = %s" % next_link)
            
            links.append(next_link)
            
            oldest_date = util.get_next_day(oldest_date)
            
            logging.info("next oldest_date = %s" % oldest_date)
            
        _template_values = {}
        _template_values["links"] = links
        _template_values["home"] = "http://%s/" % request_host
        
        _path = os.path.join(os.path.dirname(__file__), 'newsmesitemap.html')    
        
        self.response.headers["Content-Type"] = "application/xml"
        
        self.response.out.write(template.render(_path, _template_values))
