from abc import ABC, abstractmethod
from functools import reduce
import operator
import re

class FilterBase(ABC):
    """
    Abstract base class for all post filters.
    """
    @abstractmethod
    def matches(self, post):
        """
        Determine if a post matches the filter.
        
        Returns
        -------
        bool
            True if the post matches the filter.
        """
        pass
    
class NullFilter(FilterBase):
    """
    A filter that always matches any post.
    """
    def __init__(self):
        pass
    
    def matches(self, post):
        return True

class CombinationFilter(FilterBase):
    """
    Combine multiple filters with boolean operations.
    
    Attributes
    ----------
    filters: list of FilterBase
        The list of filters to combine.
    comb: str
        The boolean operation to use in combining the filters.
        Either 'and' or 'or'.
    """
    def __init__(self, filters=[], comb='and'):
        self.filters = filters
        if comb == 'and':
            self.op = operator.__and__
            self.base = True
        elif comb == 'or':
            self.op = operator.__or__
            self.base = False
        else:
            raise ValueError("Invalid combinator: {}".format(comb))
    
    def matches(self, post):
        return reduce(self.op,
                      map(lambda filt: filt.matches(post), self.filters),
                      self.base)

class Filter(FilterBase):
    """
    The concrete filter class, using regular expressions.
    
    Attributes
    ----------
    regex: str
        A Python regular expression that defines the filter.
    is_case_sensitive: bool (optional)
        Set to True if the regex is case sensitive, False otherwise.
        False by default.
    """
    def __init__(self, regex, 
                 inclusive=True,
                 is_case_sensitive=False):
        flags = 0 if is_case_sensitive else re.I
        
        self.regex_str = regex
        self.regex = re.compile(regex, flags)
        self.inclusive = inclusive
    
    @classmethod
    def FromConfig(cls, conf):
        if 'combine' in conf:
            filters = list(map(lambda c: Filter.FromConfig(c), conf.get('filters', [])))
            return CombinationFilter(filters=filters, comb=conf['combine'])
        elif 'regex' in conf:
            return Filter(regex=conf['regex'], is_case_sensitive=conf.get('case_sensitive', False))
        else:
            return NullFilter()
    
    def matches(self, post):
        b = bool(self.regex.search(post.title))
        return b if self.inclusive else (not b)