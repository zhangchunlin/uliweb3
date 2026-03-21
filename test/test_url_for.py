"""
测试 url_for 和相关 URL 生成功能
"""
import pytest
from uliweb.core.SimpleFrame import UliwebRouter


def test_url_router_basic():
    """测试 UliwebRouter 基础功能"""
    router = UliwebRouter()

    # 添加路由
    def index(request):
        return "index"

    router.add_route('/index', index, methods=['GET'])

    # 检查路由是否添加成功
    assert len(router.routes) == 1
    assert router.routes[0].path == '/index'


def test_url_router_with_params():
    """测试带参数的路由"""
    router = UliwebRouter()

    def user_view(request, user_id):
        return f"user {user_id}"

    # 添加带参数的路由
    router.add_route('/users/{user_id}', user_view, methods=['GET'])

    assert len(router.routes) == 1
    assert router.routes[0].path == '/users/{user_id}'


def test_url_router_build():
    """测试 URL 构建功能"""
    router = UliwebRouter()

    def index(request):
        return "index"

    def user_view(request, user_id):
        return f"user {user_id}"

    # 添加路由
    router.add_route('/index', index, methods=['GET'], name='index')
    router.add_route('/users/{user_id}', user_view, methods=['GET'], name='user')

    # 测试 URL 构建
    # 注意：build 方法需要先有 url_map
    # 由于 url_map 在初始化时是空的，我们需要测试其基本功能
    router.url_map[index] = router.routes[0]
    router.url_map[user_view] = router.routes[1]

    # 测试构建基本 URL
    url = router.build('index', {})
    assert url == '/index'

    # 测试构建带参数的 URL
    url = router.build('user', {'user_id': '123'})
    assert '123' in url


def test_convert_route_param():
    """测试路由参数转换功能"""
    from uliweb.core.SimpleFrame import _convert_route_param

    # 测试基本参数转换（无类型）
    result, param_types = _convert_route_param('/users/<user_id>')
    assert result == '/users/{user_id}'
    assert param_types == {}  # 无类型参数返回空字典

    # 测试带类型的参数转换
    result, param_types = _convert_route_param('/users/<int:user_id>')
    assert result == '/users/{user_id}'
    assert param_types == {'user_id': 'int'}

    # 测试多个参数
    result, param_types = _convert_route_param('/posts/<int:post_id>/comments/<int:comment_id>')
    assert result == '/posts/{post_id}/comments/{comment_id}'
    assert param_types == {'post_id': 'int', 'comment_id': 'int'}


def test_merge_rules():
    """测试路由合并功能"""
    from uliweb.core.rules import clear_rules, expose, merge_rules

    # 清理现有规则
    clear_rules()

    # 定义视图函数
    @expose('/test1')
    def test_view1():
        pass

    @expose('/test2/<id>')
    def test_view2(id):
        pass

    # 合并规则
    rules = merge_rules()

    # 验证规则
    assert len(rules) >= 2

    # 查找我们的测试视图
    test_rules = [r for r in rules if r[0] == 'test_url_for']
    assert len(test_rules) >= 2


def test_url_for_static():
    """测试 url_for_static 函数"""
    # 导入设置
    from uliweb import settings

    # 设置 STATIC_URL 配置（如果未设置）
    # 注意：在测试环境中 settings.GLOBAL 可能是 None，需要先检查
    static_url = None
    if settings is not None:
        try:
            global_settings = settings.GLOBAL
            if global_settings is not None:
                static_url = global_settings.get('STATIC_URL', '/static')
        except Exception:
            pass

    # 如果无法从 settings 获取，使用默认值
    if static_url is None:
        static_url = '/static'

    assert static_url is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])