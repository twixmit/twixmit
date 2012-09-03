
import datetime,time
import cache_keys
import logging

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

    #def get_posts_yours_pending(self,user_model,c,day):
    #    q = model.SocialPostsForUsers.all()
    #    q.filter("day_created =",day)
    #                
    #    if not c == None: q.with_cursor(c)
    #    q.filter("social_user =",user_model)
    #    q.order("created")
    #    
    #    return q
        
    #def get_posts_theirs_pending(self,c,day):
    #    q = model.SocialPostsForUsers.all()
    #    q.filter("day_created =",day)
    #                
    #    if not c == None: q.with_cursor(c)
    #    q.order("created")
    #    
    #    return q
        
    #def get_posts_yours_resubmitted(self,user_model,day):
    #    logging.info("your posts resubmitted: %s, %s" % (user_model.user_id,day) )
    #    q = model.SocialPostsForUsers.all()
    #    q.filter("day_created !=",day)            
    #    q.filter("social_user =",user_model)
    #    q.filter("resubmit =", True)
    #    #q.order("created")
    #    
    #    return q
        
    #def get_posts_theirs_resubmitted(self,user_model,day):
    #    logging.info("their posts resubmitted: %s, %s" % (user_model.user_id,day) )
    #    q = model.SocialPostsForUsers.all()
    #    q.filter("day_created !=",day)
    #    q.filter("resubmit =", True)
    #    
    #    return q                
        
    #def get_posts_demo(self):
    #    q = model.SocialDemoMixesFromFollowing.all()
    #    q.order("created")
    #    return q                
        

class Util(object):
    
    def get_expiration_stamp(self,seconds):
        gmt = GMT() 
        delta = datetime.timedelta(seconds=seconds)
        expiration = self.get_current_time()
        expiration = expiration.replace(tzinfo=gmt) 
        expiration = expiration + delta
        EXPIRATION_MASK = "%a, %d %b %Y %H:%M:%S %Z"
        
        return expiration.strftime(EXPIRATION_MASK)
    
    def get_time_from_string(self,date_string):
        dt = time.strptime(date_string, "%Y-%m-%d")
        dt = datetime.datetime(dt.tm_year, dt.tm_mon, dt.tm_mday, hour=0,minute=0)
        return dt
        
    def get_dates_stop(self,dt):
        return datetime.datetime(dt.year, dt.month, dt.day, hour=23,minute=59,second=59,microsecond=999999)
    
    def get_current_time(self):
        now = datetime.datetime.fromtimestamp(time.time())
        now = now + datetime.timedelta(hours=1)
        return now
    
    def get_todays_start(self):
        
        dt = self.get_current_time()
        day_start = datetime.datetime(dt.year, dt.month, dt.day, hour=0,minute=0)
        
        return day_start
        
    def get_todays_stop(self):
        
        dt = self.get_current_time()
        day_stop = datetime.datetime(dt.year, dt.month, dt.day, hour=23,minute=59,second=59,microsecond=999999)
        
        return day_stop
    
    def get_current_time_for_show(self):
        dt = self.get_current_time()
        for_show = datetime.datetime(dt.year, dt.month, dt.day, dt.hour,dt.minute)
        return for_show
        

    def get_time_left_in_day(self):
        dt = self.get_current_time()
        ds = self.get_todays_stop()
        
        return ds - dt
        
    def get_report_http_time_left(self):

        dt = self.get_current_time()
        
        logging.info("dt=%s" % dt)
        
        hours_left = dt.hour % cache_keys.NEWSME_DIGEST_CRON_CYCLE 
        
        logging.info("hours_left=%s" % hours_left)
        
        hour_of_last = dt.hour - hours_left
        
        logging.info("hour_of_last=%s" % hour_of_last)
        
        hour_of_next  = hour_of_last + cache_keys.NEWSME_DIGEST_CRON_CYCLE 
        
        # TODO: ValueError: hour must be in 0..23
        if hour_of_next == 24: hour_of_next = 0
        
        logging.info("hour_of_next=%s" % hour_of_next)
        
        next_time_time = datetime.datetime(dt.year, dt.month, dt.day, hour=hour_of_next,minute=0)
        
        logging.info("next_time_time=%s" % next_time_time)
        
        next_time_different = next_time_time - dt
        
        logging.info("next_time_different=%s" % next_time_different)
        
        seconds_to_cache = next_time_different.seconds
        
        logging.info("seconds_to_cache=%s" % seconds_to_cache)
        
        return seconds_to_cache
    
    #def get_next_mix_runtime(self):
    #
    #    dt = self.get_current_time()
    #    
    #    one_day = datetime.timedelta(days=1)
    #    tomorrow = dt + one_day
    #    
    #    run_time = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour=0,minute=1)
    #    
    #    return run_time