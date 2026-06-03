# 数据库使用指南

Uliweb 提供了 `uliweb.contrib.orm` 来实现数据库操作，基于 SQLAlchemy 实现 ORM 功能。

## 安装与配置

### 安装依赖

```bash
uliweb install uliweb.contrib.orm
```

这将安装：SQLAlchemy, pymysql, uliweb-alembic

### 配置 settings.ini

在 `apps/settings.ini` 中添加：

```ini
[GLOBAL]
INSTALLED_APPS = [
    'uliweb.contrib.orm',
    'uliweb.contrib.staticfiles',
    'uliweb.contrib.session',
    'myapp',
]

[ORM]
DEBUG_LOG = False
AUTO_CREATE = False
CONNECTION = 'sqlite:///database.db'
CONNECTION_ARGS = {}
CONNECTION_TYPE = 'long'
```

### ORM 配置项说明

- **DEBUG_LOG**: 设置为 True 时，SQL 语句会输出到日志
- **AUTO_CREATE**: 是否自动建表，生产环境建议关闭
- **CONNECTION**: 数据库连接串，格式：`driver://username:password@host:port/database`
- **CONNECTION_ARGS**: 额外的连接参数，传递给 SQLAlchemy 引擎
- **CONNECTION_TYPE**: 连接模式，`long` 为长连接，`short` 为短连接

### SQLite 特殊配置

SQLite 在 ASGI 等多线程环境下需要特殊配置：

```ini
[ORM]
CONNECTION = 'sqlite:///database.db'
CONNECTION_ARGS = {'poolclass': 'sqlalchemy.pool.NullPool', 'connect_args': {'check_same_thread': False}}
CONNECTION_TYPE = 'short'
```

- `poolclass = NullPool`: 禁用连接池，避免多线程问题
- `check_same_thread = False`: 允许非创建线程访问数据库

常见数据库连接串示例：

```ini
# SQLite
CONNECTION = 'sqlite:///database.db'

# MySQL
CONNECTION = 'mysql://root:password@localhost/mydb?charset=utf8'

# MySQL (pymysql)
CONNECTION = 'mysql+pymysql://root:password@localhost/mydb?charset=utf8'

# PostgreSQL
CONNECTION = 'postgres://user:password@localhost/mydb'
```

## Model 定义

在 `apps/myapp/models.py` 中定义数据模型：

```python
from uliweb.orm import *

class User(Model):
    username = Field(str, max_length=20)
    email = Field(str, max_length=128)
    created_at = Field(datetime.datetime, auto_now_add=True)

    @classmethod
    def OnInit(cls):
        # 创建索引等初始化操作
        Index('idx_username', cls.c.username, unique=True)
```

### 字段类型

| Python 类型 | 字段类 |
|------------|--------|
| str | StringProperty |
| CHAR | CharProperty |
| TEXT | TextProperty |
| int | IntegerProperty |
| float | FloatProperty |
| bool | BooleanProperty |
| datetime.datetime | DateTimeProperty |
| datetime.date | DateProperty |
| decimal.Decimal | DecimalProperty |

### 字段参数

```python
class User(Model):
    name = Field(str, max_length=50, required=True)  # 必填
    email = Field(str, unique=True)  # 唯一
    status = Field(int, default=1)  # 默认值
    created_at = Field(datetime.datetime, auto_now_add=True)  # 创建时自动填充
    updated_at = Field(datetime.datetime, auto_now=True)  # 更新时自动填充
```

## Model 注册

在 `apps/settings.ini` 中注册 Model：

```ini
[MODELS]
user = 'myapp.models.User'
```

使用 `get_model()` 获取 Model 类：

```python
from uliweb.orm import get_model

User = get_model('user')
```

## 基本操作

### 创建

```python
user = User(username='test', email='test@example.com')
user.save()
# 或
User(username='test', email='test@example.com').save()
```

### 查询

```python
# 获取单条
user = User.get(1)
user = User.get(User.c.username == 'test')

# 查询多条
users = User.all()
users = User.filter(User.c.status == 1)
users = User.filter(User.c.username.like('test%'))

# 计数
count = User.count()
count = User.filter(User.c.status == 1).count()

# 排序分页
users = User.filter().order_by(User.c.created_at.desc()).limit(10).offset(0)
```

### 更新

```python
user = User.get(1)
user.username = 'new_name'
user.save()

# 批量更新
User.filter(User.c.status == 0).update(status=1)
```

### 删除

```python
user = User.get(1)
user.delete()

# 批量删除
User.filter(User.c.status == -1).remove()
```

## 关系定义

### Reference (多对一)

```python
class Category(Model):
    name = Field(str, max_length=50)

class Article(Model):
    title = Field(str, max_length=100)
    category = Reference(Category)  # 多对一
    content = Field(TEXT)
```

使用：
```python
# 获取关联对象
article = Article.get(1)
category = article.category  # 自动触发查询

# 反向获取
category = Category.get(1)
articles = category.articles.all()  # 获取该分类下的所有文章
```

### ManyToMany (多对多)

```python
class Tag(Model):
    name = Field(str, max_length=50)

class Article(Model):
    title = Field(str)
    tags = ManyToMany(Tag)  # 多对多
```

使用：
```python
article = Article.get(1)
tag = Tag.get(1)

# 添加关系
article.tags.add(tag)

# 获取关联
tags = article.tags.all()

# 反向获取
articles = tag.articles.all()
```

### OneToOne (一对一)

```python
class Profile(Model):
    user = OneToOne(User)
    bio = Field(TEXT)
```

## 事务处理

### Web 环境自动事务

安装 `uliweb.contrib.orm` 后会自动启用事务中间件，请求成功自动提交，异常自动回滚。

### 手动事务控制

```python
from uliweb.orm import Begin, Commit, Rollback

# 开启事务
Begin()

try:
    user = User(username='test')
    user.save()
    Commit()
except:
    Rollback()
```

### 使用 with 语句

```python
from uliweb.orm import do_

with Begin():
    user = User(username='test')
    user.save()
```

## 多数据库支持

### 配置多连接

```ini
[ORM]
CONNECTION = 'mysql://root:password@localhost/maindb'

CONNECTIONS = {
    'backup': {
        'CONNECTION': 'mysql://root:password@localhost/backupdb',
        'CONNECTION_TYPE': 'short',
    }
}
```

### 指定 Model 使用特定数据库

```ini
[MODELS]
user = 'myapp.models.User'
log = 'myapp.models.Log'

[MODELS_CONFIG]
log = {'engines': ['backup']}
```

### 动态切换连接

```python
# Model 级切换
User.connect('backup')

# 查询级切换
User.filter().connect('backup')
```

## 常用 API

### get_model

```python
User = get_model('user')
```

### get_connection

```python
from uliweb.orm import get_connection
engine = get_connection('default')
```

### do_ 执行原生 SQL

```python
from uliweb.orm import do_
from sqlalchemy.sql import select

result = do_(select([User.c]))
```

## 命令行操作

```bash
# 创建数据库表
uliweb syncdb

# 重置数据库（删除并重建）
uliweb reset

# 使用 alembic 迁移
uliweb alembic init
uliweb alembic migrate
uliweb alembic upgrade
```

## 常见问题

### MySQL "MySQL server has gone away"

```ini
[ORM]
CONNECTION_ARGS = {'pool_recycle': 7200}
```

### 区分大小写查询

```python
from sqlalchemy.sql import func
User.filter(User.c.username == func.binary('Test'))
```

### update field = field + 1

```python
User.filter(User.c.id == 1).update(score=User.c.score + 1)
```

## 参考文档

- [ORM 完整文档](../docs/zh_CN/db/orm.md)
- [多数据库连接](../docs/zh_CN/db/multidb.md)
- [数据库 FAQ](../docs/zh_CN/db/faq.md)
- [ORM API](../docs/zh_CN/db/api.md)
