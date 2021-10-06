class Post:
    """
    Represents an article that can be posted by the webhook bot.
    
    Attributes
    ----------
    title: str
        The title of the article, or a short summary
    published: datetime
        The date and time the article was published or uploaded
    description: str
        An optional further description of the article
    author: str
        The name of the person or account which published or posted the article
    author_url: str
        The URL of a profile, user page, or other page relating to the author
    location: str
        Where the article was published, uploaded, or linked to.
        Example: a subreddit name
    location_url: str
        A link to where the article was linked to from.
        Example: a subreddit post (comments)
    link: str
        The URL to the article itself.
    
    """
    def __init__(self, title, published, 
                 description=None,
                 author=None, location=None, 
                 link=None, location_url=None, 
                 author_url=None,
                 image=None,
                 **kwargs):
        self.title = title
        self.published = published
        self.description = description
        self.author = author
        self.author_url = author_url
        self.location = location
        self.link = link
        self.location_url = location_url
        self.image = image
    
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
            },
            'image': {
                'url': self.image
            }
        }
        return embed
    
    def __str__(self):
        return "{}\n\tPublished: {}\n\tAuthor: {} ({})\n\tLocation: {} ({})\n\tLink: {}\n\tDescription: {}".format(
                self.title, self.published, self.author, self.author_url, self.location, 
                self.location_url, self.link, self.description)
                