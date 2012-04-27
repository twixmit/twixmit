
import social_keys,logging

from tweepy.auth import OAuthHandler
from tweepy.auth import API
from tweepy.error import TweepError
from tweepy.streaming import StreamListener,Stream
from tweepy.auth import BasicAuthHandler

class TestStreamListener(StreamListener):
    def on_status(self, status):
        print status.text
        return
        
    def on_error(self, status_code):
        logging.error(status_code)
        return False # Don't kill the stream

    def on_timeout(self):
        #print >> sys.stderr, 'Timeout...'
        logging.error('Timeout...')
        return True # Don't kill the stream

class StreamsTestsPlain(object):

    def stream(self):
        api1 = API()
        
        headers = {}
        headers["Accept-Encoding"] = "deflate, gzip"
        stream_auth = BasicAuthHandler(social_keys.TWITTER_HTTP_AUTH_U,social_keys.TWITTER_HTTP_AUTH_P)
        
        l = TestStreamListener(api=api1)
        stream = Stream(auth=stream_auth,listener=l,secure=True,headers=headers)
        
        stream.sample()
        
def main():  
    r = StreamsTestsPlain()
    r.stream()

if __name__ == '__main__':
    main()