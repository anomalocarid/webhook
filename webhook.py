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
from dateutil.parser import parse as dateutil_parse
from datetime import datetime, timezone, timedelta, MINYEAR
import requests
from bs4 import BeautifulSoup

# URLs
# Reddit
REDDIT_URL = "https://www.reddit.com/"

class Post:
    """
    Represents an article that can be posted by the webhook bot.
    
    Attributes
    ----------
    title:
        The title of the article, or a short summary
    published: datetime
        The date and time the article was published or uploaded
    description:
        An optional further description of the article
    author:
        The name of the person or account which published or posted the article
    author_url:
        The URL of a profile, user page, or other page relating to the author
    location:
        Where the article was published, uploaded, or linked to.
        Example: a subreddit name
    location_url:
        A link to where the article was linked to from.
        Example: a subreddit post (comments)
    link:
        The URL to the article itself.
    
    """
    def __init__(self, title, published, 
                 description='',
                 author='', location='', 
                 link='', location_url='', 
                 author_url=''):
        self.title = title
        self.published = published
        self.description = description
        self.author = author
        self.location = location
        self.link = link
        self.location_url = location_url
        self.author_url = author_url
    
    def make_discord_embed(self):
        embed = {
            'type': 'rich',
            'title': self.title,
            'description': self.description,
            'timestamp': self.published.isoformat(),
            'url': self.link,
            'author': {
                'name': self.author,
                'url': self.author_url
            },
            'provider': {
                'name': self.location,
                'url': self.location_url
            }
        }
        return embed

class Filter:
    def __init__(self, regex, 
                 inclusive=True,
                 is_case_sensitive=False):
        flags = 0 if is_case_sensitive else re.I
        
        self.regex = re.compile(regex, flags)
        self.inclusive = inclusive
    
    def matches(self, post):
        b = bool(self.regex.search(post.title))
        return b if self.inclusive else (not b)

"""
Split out the actual content type from the content-type header.
"""
def get_content_type(r):
    return r.headers['content-type'].split(';')[0]

def get_reddit_rss_urls():
    return ["{}r/{}/new/.rss".format(REDDIT_URL, subreddit) for subreddit in SUBREDDITS]

"""
Do a simple HTTP GET request
"""
def get_http(url, config={}):
    r = requests.get(url, headers={'user-agent': config.get('user_agent')})
    
    # rate-limit information in the headers
    rate_info = {
        'limit': r.headers.get('x-ratelimit-limit'),
        'remaining': r.headers.get('x-ratelimit-remaining'),
        'reset': r.headers.get('x-ratelimit-reset'),
        'used': r.headers.get('x-ratelimit-used'),
        'retry-at': r.headers.get('retry-at')
    }
    
    return (r, rate_info)

"""
HTTP GET + set up an XML parser
"""
def get_xml(url, config={}):
    r, rate_info = get_http(url, config)
    
    soup = BeautifulSoup(r.content, 'lxml-xml')
    return (soup, r, rate_info)

"""
Convert a reddit entry to a Post object
"""
def make_reddit_post(article):
    p = Post(title=article.get('title'),
             published=article.get('published', datetime.now()),
             author=article.get('author'),
             author_url=article.get('author_url'),
             location=article.get('subreddit'),
             location_url=article.get('comments'),
             link=article.get('link'),
             description=article.get('description'))
    return p

"""
Convert a generic RSS news feed entry to a Post object
"""
def make_news_post(article):
    p = Post(title=article.get('title'),
             published=article.get('published', datetime.now()),
             author=article.get('author'),
             link=article.get('link'),
             description=article.get('description'),
             location=article.get('location'),
             location_url=article.get('location_url'))
    return p

"""
Parse a reddit RSS feed
"""
def get_reddit(url, config={}):
    soup, resp, rate_info = get_xml(url, config)
    
    entries = soup.findAll('entry')
    articles = []
    for entry in entries:
        article = {
            'title': entry.find('title').text,
            'published': datetime.fromisoformat(entry.find('published').text),
            'subreddit': ''
        }
        # Author information
        author = entry.find('author')
        article['author'] = author.find('name').text
        article['author_url'] = author.find('uri').text
        # Extract external link and link to comments from the post
        content = BeautifulSoup(entry.find('content').text, "html.parser")
        links = list(filter(lambda a: a.text == '[link]', content.findAll('a')))
        if len(links) > 0:
            link = links[0]['href']
            article['link'] = link
        comments = list(filter(lambda a: a.text == '[comments]', content.findAll('a')))
        # Link to comments
        if len(comments) > 0:
            comment = comments[0]['href']
            article['comments'] = comment
            article['subreddit'] = '/r/{}'.format(comment.split('/')[4])
        # Make a description
        article['description'] = 'Posted by {} in {} <{}>.'.format(article.get('author'),
                                                                   article.get('subreddit'),
                                                                   article.get('comments'))
        
        articles.append(article)
    
    return rate_info, articles

"""
Parse a generic RSS feed
"""
def get_rss(url, config={}):
    soup, resp, rate_info = get_xml(url, config)
    
    items = soup.findAll('item')
    channel = soup.find('channel')
    articles = []
    for item in items:
        article = {
            'title': item.find('title').text,
            'published': dateutil_parse(item.find('pubDate').text),
            'description': item.find('description').text,
            'link': item.find('link').text,
            'location': channel.find('title').text,
            'location_url': channel.find('link').text
        }

        articles.append(article)
    
    return rate_info, articles
    

"""
Process main for Reddit scraping
"""
def reddit_main(posts, config):
    updates = dict()
    # can combine multiple subreddits into one request
    full_url = '{}r/{}/new/.rss'.format(REDDIT_URL, '+'.join(config.get('subreddits')))
    while True:
        try:
            rate_info, articles = get_reddit(full_url, config)
            latest = updates.get(full_url, datetime.now(timezone.utc) - timedelta(seconds=10)) 
            new_posts = map(make_reddit_post, 
                         filter(lambda a: a['published'] > latest, articles))
            updates[full_url] = max([a['published'] for a in articles]) # use last updated article on reddit's side
            for post in new_posts:
                posts.put(post)
        except Exception as e:
            print("Something went wrong:", e)
        time.sleep(60.0) # reddit is pretty slow, so take a break

def rss_main(posts, config):
    updates = dict()
    urls = config.get("feeds", [])
    while True:
        new_posts = []
        for url in urls:
            try:
                rate_info, articles = get_rss(url, config)
                latest = updates.get(url, datetime.now(timezone.utc) - timedelta(seconds=10))
                new_posts += list(map(make_news_post,
                             filter(lambda a: a['published'] > latest, articles)))
                updates[url] = max([a['published'] for a in articles])
                time.sleep(1.0)
            except Exception as e:
                print("Something went wrong:", e)
        for post in new_posts:
            posts.put(post)
        time.sleep(60.0)

if __name__ == "__main__":
    config_file = 'config.json' if len(sys.argv) < 2 else argv[1]
    with open(config_file, "r") as f:
        config = json.load(f)
    
    filters = []
    for f in config.get('filters', []):
        filt = Filter(regex=f.get('regex', ''), 
                      inclusive=f.get('inclusive', True))
        filters.append(filt)
    
    post_queue = Queue()
    reddit_process = Process(target=reddit_main, args=(post_queue,config))
    reddit_process.start()
    rss_process = Process(target=rss_main, args=(post_queue, config))
    rss_process.start()

    while True:
        post = post_queue.get()
        filtered = False
        for filt in filters:
            filtered = not filt.matches(post)
            if filtered:
                print('FILTER: removed post "{}"'.format(post.title))
                break
        
        if not filtered:
            print('POST: "{}"'.format(post.title))
            try:
                post = post.make_discord_embed()
                r = requests.post(config.get('webhook_url'), 
                                  json={'embeds': [post]})
            except Exception as e:
                print("Something went wrong:", e)
            time.sleep(5.0)
    
