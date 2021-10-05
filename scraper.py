from datetime import datetime, timezone, timedelta
import requests
import sys
import traceback

from dateutil.parser import parse as dateutil_parse
from dateutil.tz import gettz
from bs4 import BeautifulSoup

from post import Post

# Timezone information
TZINFOS = {
    "EDT": gettz("Eastern Daylight Time"),
    "IST": gettz("India Standard Time")
}

"""
Split out the actual content type from the content-type header.
"""
def get_content_type(r):
    return r.headers['content-type'].split(';')[0]

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

class Scraper:
    def __init__(self, source='rss', config={}):
        self.config = config
        self.source = source
        self.updates = dict()
    
    def get_url(self, url):
        soup, resp, rate_info = get_xml(url, self.config)
        
        if self.source == 'rss':
            self._channel = soup.find('channel')
        
        items = self._get_items(soup)
        articles = []
        for item in items:
            if self.source == 'reddit':
                self._content = BeautifulSoup(item.find('content').text, "html.parser")
                self._comments = [a for a in self._content.findAll('a') if a.text == '[comments]']
            item = {
                'title': self._get_title(item),
                'published': self._get_datetime(item),
                'link': self._get_link(item),
                'author': self._get_author(item),
                'author_url': self._get_author_url(item),
                'location': self._get_location(item),
                'location_url': self._get_location_url(item),
                'description': self._get_description(item)
            }
            articles.append(item)
        
        latest = self.updates.get(url, datetime.now(timezone.utc) - timedelta(seconds=10))
        self.updates[url] = max([a['published'] for a in articles])
        articles = filter(lambda a: a['published'] > latest, articles)
        
        return list(map(lambda a: Post(**a), articles))
    
    def make_post(self, article):
        return Post(**article)

    def _get_items(self, soup):
        if self.source == 'rss':
            return soup.findAll('item')
        elif self.source == 'reddit':
            return soup.findAll('entry')
    
    def _get_title(self, item):
        if self.source in ['reddit', 'rss']:
            return item.find('title').text
    
    def _get_datetime(self, item):
        if self.source == 'reddit':
            return datetime.fromisoformat(item.find('published').text)
        elif self.source == 'rss':
            return dateutil_parse(item.find('pubDate').text, tzinfos=TZINFOS)
    
    def _get_link(self, item):
        if self.source == 'reddit':
            links = [a for a in self._content.findAll('a') if a.text == '[link]']
            if len(links) > 0:
                return links[0]['href']
            else:
                return None
        elif self.source == 'rss':
            return item.find('link').text
    
    def _get_author(self, item):
        if self.source == 'reddit':
            return item.find('author').find('name').text
        elif self.source == 'rss':
            return None # TODO
    
    def _get_author_url(self, item):
        if self.source == 'reddit':
            return item.find('author').find('uri').text
        elif self.source == 'rss':
            return None # TODO

    def _get_location(self, item):
        if self.source == 'reddit':
            if len(self._comments) > 0:
                comment = self._comments[0]['href']
                return '/r/{}'.format(comment.split('/')[4])
            else:
                return None
        elif self.source == 'rss':
            return self._channel.find('title').text

    def _get_location_url(self, item):
        if self.source == 'reddit':
            if len(self._comments) > 0:
                comment = self._comments[0]['href']
                return '/r/{}'.format(comment.split('/')[4])
            else:
                return None
        elif self.source == 'rss':
            return self._channel.find('link').text
    
    def _get_description(self, item):
        if self.source == 'reddit':
            return 'Posted by {} in {} <{}>'.format(self._get_author(item),
                                                    self._get_location(item),
                                                    self._get_location_url(item))
        elif self.source == 'rss':
            return item.find('description').text
