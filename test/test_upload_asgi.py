import os
import shutil
import tempfile
from uliweb import manage
from uliweb.utils.test import client_from_application


def test_upload_asgi():
    """
    测试文件上传模块的 ASGI 兼容性
    """
    # 创建临时项目目录
    project_dir = tempfile.mkdtemp(prefix='test_upload_asgi_')

    try:
        # 切换到项目目录
        old_cwd = os.getcwd()
        os.chdir(project_dir)

        # 创建项目
        manage.call('uliweb makeproject -y .')

        # 创建应用
        app = manage.make_simple_application(
            project_dir=project_dir,
            include_apps=['uliweb.contrib.upload'],
            reuse=False
        )

        # 创建测试客户端
        c = client_from_application(app)

        # 测试文件服务路由是否存在
        result = c.get('/uploads/test.txt')
        # 应该返回 404 而不是其他错误
        assert result.status_code in [404, 403], f"Expected 404 or 403, got {result.status_code}"

        print("Upload ASGI test passed")

    finally:
        # 恢复工作目录
        os.chdir(old_cwd)
        # 清理临时目录
        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == '__main__':
    test_upload_asgi()
