POSTS_DAY_START = "posts_day_start"
POSTS_DAY_STOP  = "posts_day_stop"
POST_RESULTS = "posts_results_%s_%s_%s"
POSTS_DEMO = "posts_demo"
NOW_TIME = "now_time"

NEWSME_REPORTHANDLER_ALL_STORIES = "NewsmeDigestionReportHandler_NewsMeDigestionStoryModel_%s"
NEWSME_DIGESTPAGE_HTML = "NewsmeDigestionPageHtml_%s"

# runs every 3 hours, but digest pages are the same
# all day, but we only crawl to a limit, so we cycle
NEWSME_DIGEST_CRON_CYCLE = 3 # hours
NEWSME_CACHE_DIGEST_RESPONSE = 28800 # 8 hours
