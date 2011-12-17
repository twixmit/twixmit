
from google.appengine.api import memcache
from google.appengine.api import users

import model
import datetime,time
import cache_keys

class Util(object):
    
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