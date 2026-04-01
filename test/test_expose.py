from uliweb.core.rules import expose, clear_rules, merge_rules, set_app_rules
import uliweb.core.rules as rules

def test():
    """
    >>> clear_rules()
    >>> @expose
    ... def index():pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.index', '/test_expose/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... def index(id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.index', '/test_expose/index/<id>', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose()
    ... def index():pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.index', '/test_expose/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose()
    ... def index(id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.index', '/test_expose/index/<id>', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/index')
    ... def index():pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.index', '/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose(static=True)
    ... def index():pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.index', '/test_expose/index', {'static': True, 'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/index')
    ... def index(id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.index', '/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:pass
    >>> print(merge_rules())
    []
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     def index(self):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/test_expose/A/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/test_expose/A/index/<id>', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     @expose('/index')
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/user')
    ... class A:
    ...     @expose('/index')
    ...     def index(self, id):pass
    ...     def hello(self):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.hello', '/user/hello', {'methods': ['GET', 'POST', 'PUT']}), ('test_expose', 'test_expose.A.index', '/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/user')
    ... class A(object):
    ...     @expose('/index')
    ...     def index(self, id):pass
    ...     def hello(self):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.hello', '/user/hello', {'methods': ['GET', 'POST', 'PUT']}), ('test_expose', 'test_expose.A.index', '/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> app_rules = {'test_expose':'/wiki'}
    >>> set_app_rules(app_rules)
    >>> @expose('/user')
    ... class A(object):
    ...     @expose('/index')
    ...     def index(self, id):pass
    ...     def hello(self):pass
    ...     @expose('inter')
    ...     def inter(self):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.hello', '/wiki/user/hello', {'methods': ['GET', 'POST', 'PUT']}), ('test_expose', 'test_expose.A.index', '/wiki/index', {'methods': ['GET', 'POST', 'PUT']}), ('test_expose', 'test_expose.A.inter', '/wiki/user/inter', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> rules.__app_rules__ = {}
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     @expose('/index', name='index', static=True)
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/index', {'static': True, 'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> set_app_rules({})
    >>> @expose
    ... class A:
    ...     @expose
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/test_expose/A/index/<id>', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> set_app_rules({})
    >>> @expose
    ... class A:
    ...     @expose()
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/test_expose/A/index/<id>', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     @expose(name='index', static=True)
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/test_expose/A/index/<id>', {'static': True, 'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/')
    ... class A:
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/index/<id>', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> def static():pass
    >>> n = expose('/static', static=True)(static)
    >>> print(merge_rules())
    [('test_expose', 'test_expose.static', '/static', {'static': True, 'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     @expose('/index', name='index', static=True)
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/index', {'static': True, 'methods': ['GET', 'POST', 'PUT']})]
    >>> print(rules.__url_names__)
    {'index': 'test_expose.A.index'}
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/')
    ... class A:
    ...     @expose('index/<id>')
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/index/<id>', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     @expose('index')
    ...     def index(self, id):pass
    >>> print(merge_rules())
    [('test_expose', 'test_expose.A.index', '/test_expose/A/index', {'methods': ['GET', 'POST', 'PUT']})]
    >>> clear_rules()

    """

# if __name__ == '__main__':
#    @expose
#    class A(object):
#        @expose('index')
#        def index(self, id):pass
#        def hello(self):pass
#    print(merge_rules())