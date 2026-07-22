#coding=utf-8
"""
测试 ManyToMany 关系中 .with_relation() 返回的对象 id 为 None 的问题

参考: /home/zhangclb/sandbox/ai_mcp/knowbot/doc/rbac_manytoone_role_id_none.md

问题描述：
在使用 Uliweb ORM 的 ManyToMany 关系时，通过 .with_relation() 获取关联对象时，
返回的对象的 id 字段为 None，但其他字段（如 name）是正常的。
"""
import sys
sys.path.insert(0, '../uliweb/lib')
from uliweb.orm import *
import uliweb.orm
uliweb.orm.__auto_create__ = True
uliweb.orm.__nullable__ = True
uliweb.orm.__server_default__ = False


def cleanup_models():
    """清理测试中定义的模型，避免影响其他测试"""
    models_to_remove = ['permission', 'role', 'role_perm_rel', 'user']
    for name in models_to_remove:
        if name in uliweb.orm.__models__:
            del uliweb.orm.__models__[name]
        for engine_name in uliweb.orm.engine_manager.engines:
            engine = uliweb.orm.engine_manager.get(engine_name)
            if name in engine.models:
                del engine.models[name]


def test_rbac_scenario():
    """
    复现 RBAC 场景中的问题

    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> db.metadata.clear()

    定义与 rbac/models.py 中类似的模型：

    >>> class Permission(Model):
    ...     name = Field(str, max_length=80, required=True)
    >>> class Role(Model):
    ...     name = Field(str, max_length=80, required=True)
    ...     permissions = ManyToMany('permission', through='role_perm_rel',
    ...                              collection_name='perm_roles')
    >>> class Role_Perm_Rel(Model):
    ...     role = Reference('role')
    ...     permission = Reference('permission')

    创建测试数据：

    >>> role1 = Role(name='sys_reader')
    >>> role1.save()
    True
    >>> role2 = Role(name='superuser')
    >>> role2.save()
    True
    >>> perm = Permission(name='sys_access')
    >>> perm.save()
    True

    建立关联：

    >>> role1.permissions.add(perm)
    True
    >>> role2.permissions.add(perm)
    True

    从 Permission 端查询关联的 Roles：

    >>> perm_obj = Permission.get(Permission.c.name == 'sys_access')
    >>> roles = list(perm_obj.perm_roles.with_relation().all())
    >>> len(roles)
    2

    核心断言：id 不应该为 None

    >>> for role in roles:
    ...     assert role.id is not None, f"Role '{role.name}' should have id, got None"

    核心断言：to_dict()["id"] 不应该是 Lazy 类型

    >>> for role in roles:
    ...     d = role.to_dict()
    ...     assert d['id'] is not Lazy, f"Role '{role.name}' to_dict()['id'] should not be Lazy, got {d['id']}"

    测试完成后清理：

    >>> cleanup_models()
    """


def test_rbac_scenario_with_debug():
    """
    带调试输出的测试，用于查看 with_relation() 返回对象的详细信息

    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> db.metadata.clear()

    定义与 rbac/models.py 中类似的模型（User 必须在 Role 之前定义）：

    >>> class User(Model):
    ...     username = Field(str, max_length=80)
    >>> class Permission(Model):
    ...     name = Field(str, max_length=80, required=True)
    >>> class Role(Model):
    ...     name = Field(str, max_length=80, required=True)
    ...     users = ManyToMany('user', collection_name='user_roles')
    ...     permissions = ManyToMany('permission', through='role_perm_rel',
    ...                              collection_name='perm_roles')
    >>> class Role_Perm_Rel(Model):
    ...     role = Reference('role')
    ...     permission = Reference('permission')

    创建测试数据：

    >>> role1 = Role(name='sys_reader')
    >>> role1.save()
    True
    >>> role2 = Role(name='superuser')
    >>> role2.save()
    True
    >>> perm = Permission(name='sys_access')
    >>> perm.save()
    True
    >>> user = User(username='testuser')
    >>> user.save()
    True

    建立关联：

    >>> role1.permissions.add(perm)
    True
    >>> role2.permissions.add(perm)
    True
    >>> role1.users.add(user)
    True

    直接查询验证：

    >>> direct_role = Role.get(Role.c.name == 'sys_reader')
    >>> print(f"Direct query: role.id={direct_role.id}, role.name={direct_role.name}")
    Direct query: role.id=1, role.name=sys_reader

    使用 with_relation() 从 Permission 端查询：

    >>> perm_obj = Permission.get(Permission.c.name == 'sys_access')
    >>> roles = list(perm_obj.perm_roles.with_relation().all())
    >>> for role in roles:
    ...     print(f"with_relation: role.id={role.id}, role.name={role.name}")
    with_relation: role.id=1, role.name=sys_reader
    with_relation: role.id=2, role.name=superuser

    核心断言：id 不应该为 None

    >>> for role in roles:
    ...     assert role.id is not None, f"Role '{role.name}' should have id, got None"

    核心断言：to_dict()["id"] 不应该是 Lazy 类型

    >>> for role in roles:
    ...     d = role.to_dict()
    ...     assert d['id'] is not Lazy, f"Role '{role.name}' to_dict()['id'] should not be Lazy, got {d['id']}"

    测试 has() 方法是否正常工作：

    >>> for role in roles:
    ...     if role.name == 'sys_reader':
    ...         result = role.users.has(user)
    ...         print(f"role.users.has(user) = {result}")
    role.users.has(user) = True

    测试完成后清理：

    >>> cleanup_models()
    """


def test_to_dict_id_not_lazy():
    """
    测试 to_dict() 返回的 id 字段不应该是 Lazy 类型

    这是针对问题的核心测试：ManyToMany with_relation() 返回的对象
    的 id 字段在 to_dict() 中应该是实际值，而不是 Lazy 延迟加载对象。

    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> db.metadata.clear()

    定义模型：

    >>> class Permission(Model):
    ...     name = Field(str, max_length=80, required=True)
    ...     description = Field(str, max_length=255)
    >>> class Role(Model):
    ...     name = Field(str, max_length=80, required=True)
    ...     description = Field(str, max_length=255)
    ...     reserve = Field(bool)
    ...     permissions = ManyToMany('permission', through='role_perm_rel',
    ...                              collection_name='perm_roles')
    >>> class Role_Perm_Rel(Model):
    ...     role = Reference('role')
    ...     permission = Reference('permission')

    创建测试数据：

    >>> role1 = Role(name='sys_reader', description='System reader', reserve=True)
    >>> role1.save()
    True
    >>> perm = Permission(name='sys_access', description='System access')
    >>> perm.save()
    True
    >>> role1.permissions.add(perm)
    True

    使用 with_relation() 获取关联对象：

    >>> perm_obj = Permission.get(Permission.c.name == 'sys_access')
    >>> roles = list(perm_obj.perm_roles.with_relation().all())

    检查 to_dict() 返回的 id 不是 Lazy：

    >>> for role in roles:
    ...     d = role.to_dict()
    ...     # id 应该是实际值，不应该是 Lazy 类型
    ...     assert d['id'] is not Lazy, f"to_dict()['id'] should not be Lazy, got {d['id']}"
    ...     # id 应该是整数类型
    ...     assert isinstance(d['id'], int), f"to_dict()['id'] should be int, got {type(d['id'])}"

    测试完成后清理：

    >>> cleanup_models()
    """


def test_with_relation_and_fields():
    """
    测试 with_relation() 和 fields() 组合使用时返回对象的 id 正确

    这个测试验证 ManyToMany with_relation() 结合 fields() 方法使用时，
    返回的对象应该有正确的 id 值。

    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()
    >>> db.metadata.clear()

    定义模型：

    >>> class Permission(Model):
    ...     name = Field(str, max_length=80, required=True)
    ...     description = Field(str, max_length=255)
    >>> class Role(Model):
    ...     name = Field(str, max_length=80, required=True)
    ...     description = Field(str, max_length=255)
    ...     reserve = Field(bool)
    ...     permissions = ManyToMany('permission', through='role_perm_rel',
    ...                              collection_name='perm_roles')
    >>> class Role_Perm_Rel(Model):
    ...     role = Reference('role')
    ...     permission = Reference('permission')

    创建测试数据：

    >>> role1 = Role(name='sys_reader', description='System reader', reserve=True)
    >>> role1.save()
    True
    >>> role2 = Role(name='superuser', description='Super user', reserve=False)
    >>> role2.save()
    True
    >>> perm = Permission(name='sys_access', description='System access')
    >>> perm.save()
    True
    >>> role1.permissions.add(perm)
    True
    >>> role2.permissions.add(perm)
    True

    使用 with_relation() + fields() 获取关联对象：

    >>> perm_obj = Permission.get(Permission.c.name == 'sys_access')
    >>> mm = perm_obj.perm_roles.with_relation()
    >>> _ = mm.fields('name', 'description')
    >>> roles = list(mm.all())

    验证返回的对象数量正确：

    >>> len(roles)
    2

    验证返回的对象有正确的 id（不是 None）：

    >>> for role in roles:
    ...     assert role.id is not None, f"Role '{role.name}' should have id, got None"

    验证 to_dict()["id"] 不是 Lazy 类型：

    >>> for role in roles:
    ...     d = role.to_dict()
    ...     assert d['id'] is not Lazy, f"to_dict()['id'] should not be Lazy, got {d['id']}"
    ...     assert isinstance(d['id'], int), f"to_dict()['id'] should be int, got {type(d['id'])}"

    测试完成后清理：

    >>> cleanup_models()
    """


if __name__ == '__main__':
    import doctest
    results = doctest.testmod(verbose=True)
    print(f"\nDoctest: {results.attempted} tests, {results.failed} failures")