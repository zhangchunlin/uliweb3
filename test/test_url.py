import time, sys
sys.path.insert(0, '../uliweb/lib')
from uliweb import expose
from uliweb.core import rules
from uliweb.utils.sorteddict import SortedDict

def test_1():
    """
    >>> rules.__exposes__ = SortedDict() # reset exposes
    >>> def view():pass
    >>> f = expose('!/')(view)
    >>> rules.merge_rules()
    [('test_url', 'test_url.view', '/', {'methods': ['GET', 'POST', 'PUT']})]
    >>> f = expose('/hello')(view)
    >>> rules.merge_rules()
    [('test_url', 'test_url.view', '/', {'methods': ['GET', 'POST', 'PUT']}), ('test_url', 'test_url.view', '/hello', {'methods': ['GET', 'POST', 'PUT']})]
    >>> @expose('/test')
    ... class TestView(object):
    ...     @expose('')
    ...     def index(self):
    ...         return {}
    ...
    ...     @expose('!/ttt')
    ...     def ttt(self):
    ...         return {}
    ...
    ...     @expose('/print')
    ...     def pnt(self):
    ...         return {}
    >>> rules.merge_rules()
    [('test_url', 'test_url.view', '/', {'methods': ['GET', 'POST', 'PUT']}), ('test_url', 'test_url.view', '/hello', {'methods': ['GET', 'POST', 'PUT']}), ('test_url', 'test_url.TestView.index', '/test', {'methods': ['GET', 'POST', 'PUT']}), ('test_url', 'test_url.TestView.pnt', '/print', {'methods': ['GET', 'POST', 'PUT']}), ('test_url', 'test_url.TestView.ttt', '/ttt', {'methods': ['GET', 'POST', 'PUT']})]
    """