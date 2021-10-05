"""
A webhook news feed bot for Discord.

Right now it only supports reddit and has no filtering capabilities.
I plan on adding more sources in the future, as well as options for filtering.

Copyright 2021 Anomalocaris

Permission is hereby granted, free of charge, to any person obtaining a copy 
of this software and associated documentation files (the "Software"), to deal 
in the Software without restriction, including without limitation the rights 
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
copies of the Software, and to permit persons to whom the Software is 
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in 
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
DEALINGS IN THE SOFTWARE.
"""
import time, json, sys, re
from multiprocessing import Pool, Process, Queue
import traceback
from dateutil.parser import parse as dateutil_parse
from dateutil.tz import gettz
from datetime import datetime, timezone, timedelta, MINYEAR
import requests
from bs4 import BeautifulSoup

from post import Post
from filter import Filter
from scraper import Scraper

# URLs
# Reddit
REDDIT_URL = "https://www.reddit.com/"

# Default time to wait between checking for new posts, in seconds
DEFAULT_CHECK_COOLDOWN = 60.0

"""
Process main for Reddit scraping
"""
def reddit_main(posts, config):
    check_cooldown = config.get('reddit_check_cooldown',
                                config.get('check_cooldown', DEFAULT_CHECK_COOLDOWN))
    scraper = Scraper(source='reddit', config=config)
    
    # can combine multiple subreddits into one request
    full_url = '{}r/{}/new/.rss'.format(REDDIT_URL, '+'.join(config.get('subreddits')))
    while True:
        try:
            new_posts = scraper.get_url(full_url)
        except Exception as e:
            print(traceback.format_exc())
            new_posts = []
        for post in new_posts:
            posts.put(post)
        time.sleep(check_cooldown)

def rss_main(posts, config):
    check_cooldown = config.get('rss_check_cooldown',
                                config.get('check_cooldown', DEFAULT_CHECK_COOLDOWN))
    scraper = Scraper(source='rss', config=config)
    urls = config.get("feeds", [])
    while True:
        new_posts = []
        for url in urls:
            try:
                new_posts += scraper.get_url(url)
                time.sleep(5.0)
            except Exception as e:
                print(traceback.format_exc())
        for post in new_posts:
            posts.put(post)
        time.sleep(check_cooldown)

if __name__ == "__main__":
    config_file = 'config.json' if len(sys.argv) < 2 else argv[1]
    with open(config_file, "r") as f:
        config = json.load(f)
    
    filt = Filter.FromConfig(config.get('filter', {}))
    
    post_queue = Queue()
    reddit_process = Process(target=reddit_main, args=(post_queue,config))
    reddit_process.start()
    rss_process = Process(target=rss_main, args=(post_queue, config))
    rss_process.start()

    while True:
        post = post_queue.get()
        
        if filt.matches(post):
            print('POST:', post)
            try:
                post = post.make_discord_embed()
                r = requests.post(config.get('webhook_url'), 
                                  json={'embeds': [post]})
            except Exception as e:
                print("Something went wrong:", e)
            time.sleep(5.0)
        else:
            print('FILTER: removed post', post)
    
