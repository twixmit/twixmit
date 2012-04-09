
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db

import model
import datetime,time
import cache_keys
import logging
import hashlib
import social_keys

#http://groups.google.com/group/google-appengine-python/browse_thread/thread/c4e4c9417fb0a5fb
class GMT(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=10) # + self.dst(dt)
    def tzname(self, dt):
        return "GMT"
    def dst(self, dt):
        return datetime.timedelta(0) 

class Queries(object):

    def get_db_run_config_eventual(self):
        return db.create_config(deadline=5, read_policy=db.EVENTUAL_CONSISTENCY)

    def get_posts_yours_pending(self,user_model,c,day):
        q = model.SocialPostsForUsers.all()
        q.filter("day_created =",day)
                    
        if not c == None: q.with_cursor(c)
        q.filter("social_user =",user_model)
        q.order("created")
        
        return q
        
    def get_posts_theirs_pending(self,c,day):
        q = model.SocialPostsForUsers.all()
        q.filter("day_created =",day)
                    
        if not c == None: q.with_cursor(c)
        q.order("created")
        
        return q
        
    def get_posts_yours_resubmitted(self,user_model,day):
        logging.info("your posts resubmitted: %s, %s" % (user_model.user_id,day) )
        q = model.SocialPostsForUsers.all()
        q.filter("day_created !=",day)            
        q.filter("social_user =",user_model)
        q.filter("resubmit =", True)
        #q.order("created")
        
        return q
        
    def get_posts_theirs_resubmitted(self,user_model,day):
        logging.info("their posts resubmitted: %s, %s" % (user_model.user_id,day) )
        q = model.SocialPostsForUsers.all()
        q.filter("day_created !=",day)
        q.filter("resubmit =", True)
        
        return q                
        
    def get_posts_demo(self):
        q = model.SocialDemoMixesFromFollowing.all()
        q.order("created")
        return q                
        

class Util(object):
    
    def get_expiration_stamp(self,seconds):
        gmt = GMT() 
        delta = datetime.timedelta(seconds=seconds)
        expiration = self.get_current_time()
        expiration = expiration.replace(tzinfo=gmt) 
        expiration = expiration + delta
        EXPIRATION_MASK = "%a, %d %b %Y %H:%M:%S %Z"
        
        return expiration.strftime(EXPIRATION_MASK)
            
    
    def is_user_viacookie_good(self,request):
        if "twitter_anywhere_identity" in request.cookies.keys():
            user_sig_pair = request.cookies["twitter_anywhere_identity"]
            user = user_sig_pair.split(":")[0]
            sig = user_sig_pair.split(":")[1]
            
            m = hashlib.sha1()
            m.update(user + social_keys.TWITTER_CONSUMER_SECRET)
            if m.digest() == sig:
            
            else:
                return None
        else:
            return None
             
            
            
            
    
    def is_user_good(self):
        user = users.get_current_user()
        if user:
            social_users = model.SocialKeysForUsers.all()
            social_users.filter("user_id =",user.user_id())
            user_model = social_users.get()
            
            if user_model.access_token_key and user_model.access_token_secret:
                return user_model
            else:
                return None
        else:
            return None
            
    def get_twitter_user(self,api,user):
        twitter_user = memcache.get("twitter_user:%s" % user.user_id())
                        
        if twitter_user == None:
            twitter_user = api.me()
            memcache.add("twitter_user:%s" % user.user_id(), twitter_user, 60)
        
        return twitter_user
    
    def get_current_time(self):
        now = memcache.get(cache_keys.NOW_TIME)
        
        if now == None:
            now = datetime.datetime.fromtimestamp(time.time())
            memcache.add(cache_keys.NOW_TIME, now, 10)
            
        return now
    
    def get_todays_start(self):
        
        day_start = memcache.get(cache_keys.POSTS_DAY_START)
        
        if day_start == None:
            dt = self.get_current_time()
            day_start = datetime.datetime(dt.year, dt.month, dt.day, hour=0,minute=0)
            memcache.add(cache_keys.POSTS_DAY_START, day_start, 60)
        
        return day_start
        
    def get_todays_stop(self):
        day_stop = memcache.get(cache_keys.POSTS_DAY_STOP)
        
        if day_stop == None:
            dt = self.get_current_time()
            day_stop = datetime.datetime(dt.year, dt.month, dt.day, hour=23,minute=59,second=59,microsecond=999999)
            memcache.add(cache_keys.POSTS_DAY_START, day_stop, 60)
        
        return day_stop
    
    def get_current_time_for_show(self):
        dt = self.get_current_time()
        for_show = datetime.datetime(dt.year, dt.month, dt.day, dt.hour,dt.minute)
        return for_show
    
    def get_next_mix_runtime(self):
    
        dt = self.get_current_time()
        
        one_day = datetime.timedelta(days=1)
        tomorrow = dt + one_day
        
        run_time = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour=0,minute=1)
        
        return run_time