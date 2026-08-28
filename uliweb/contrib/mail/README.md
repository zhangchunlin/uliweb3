# uliweb.contrib.mail

邮件发送 App，基于 Uliweb3 提供异步邮件发送能力。封装了 Python 标准库 `smtplib` / `email`，支持 SMTP、GMail、本机 sendmail 三种后端，并支持纯文本、HTML、抄送、附件及多收件人。

## 特性

- **异步发送**：`Mail.send_mail()` 为 `async` 方法，内部通过协程池（`anyio.to_thread.run_sync`）执行同步操作，不阻塞事件循环。
- **多后端**：内置 SMTP、GMail、Sendmail 三种后端，通过配置自由切换，也可自定义后端。
- **富内容支持**：支持 HTML 正文、抄送（CC）、多收件人（逗号分隔 / 列表）。
- **附件支持**：自动根据 MIME 类型（文本、图片、音频、二进制等）生成附件，支持 Unicode 文件名。
- **Unicode 友好**：正文、主题、附件均正确处理中文字符与编码。
- **零配置默认**：未配置时默认使用本地 SMTP（`localhost:25`）。

## 架构

```
uliweb/contrib/mail/          # App 包
├── README.md                 # 本文档
├── conf.py                   # 管理表单（当前为空，可扩展配置界面）
├── info.ini                  # App 元信息（用于应用管理界面）
├── settings.ini              # [MAIL] 段默认配置
└── __init__.py               # App 标识（空文件）

uliweb/mail/                  # 核心实现（独立于 App 包）
├── __init__.py               # EmailMessage / Mail / BaseMailConnection
└── backends/
    ├── smtp.py               # SMTP 后端
    ├── gmail.py              # GMail（TLS）后端
    └── sendmail.py           # 本机 sendmail 后端
```

邮件核心逻辑位于 `uliweb/mail`，`uliweb/contrib/mail` 作为 Uliweb App 提供 `settings.ini` 默认配置与元信息，二者配合使用。

## 安装与注册

将 `uliweb.contrib.mail` 加入项目的 `INSTALLED_APPS`：

```ini
[GLOBAL]
INSTALLED_APPS = [
    'uliweb.contrib.staticfiles',
    'uliweb.contrib.mail',
]
```

## 配置

App 提供如下默认配置（`uliweb/contrib/mail/settings.ini`），可在项目 `settings.ini` 中覆盖：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `MAIL/HOST` | `'localhost'` | SMTP 服务器地址 |
| `MAIL/PORT` | `25` | SMTP 端口 |
| `MAIL/USER` | `''` | 认证用户名 |
| `MAIL/PASSWORD` | `''` | 认证密码 |
| `MAIL/BACKEND` | `'uliweb.mail.backends.smtp'` | 后端模块路径 |
| `MAIL/SENDMAIL_LOCATION` | `'/usr/sbin/sendmail'` | sendmail 可执行文件路径 |

配置示例（使用 465/587 端口的外部 SMTP 服务）：

```ini
[MAIL]
HOST = 'smtp.example.com'
PORT = 587
USER = 'noreply@example.com'
PASSWORD = 'your-password'
BACKEND = 'uliweb.mail.backends.smtp'
```

> 按 Uliweb 配置约定，配置读取主要有两种方式（以 `MAIL/HOST` 为例）：
>
> ```python
> from uliweb import settings
>
> # 常用写法（推荐）：属性访问
> settings.MAIL.HOST
>
> # 通用写法：get_var（斜杠路径）
> settings.get_var('MAIL/HOST')
> ```
>
> 视图函数中 `settings` 已自动注入，可直接使用。

## 后端

| 后端 | BACKEND 值 | 说明 |
| --- | --- | --- |
| SMTP | `'uliweb.mail.backends.smtp'`（默认） | 标准 SMTP，按需登录 |
| GMail | `'uliweb.mail.backends.gmail'` | 使用 STARTTLS + 登录，默认 `smtp.gmail.com:587` |
| Sendmail | `'uliweb.mail.backends.sendmail'` | 调用本机 `sendmail` 命令，无需网络连接 |

自定义后端需在指定模块中实现 `MailConnection` 类，继承 `BaseMailConnection` 并实现：

- `get_connection()`：建立连接
- `send_mail(from_, to_, message)`：发送邮件
- `close()`：关闭连接
- （可选）`login()`：认证

## 使用

### 1. 发送邮件

`Mail` 对象构造参数与配置项一一对应，缺省时自动读取 `settings`：

```python
from uliweb import expose
from uliweb.mail import Mail

@expose('/send')
async def send():
    mail = Mail()
    await mail.send_mail(
        'noreply@example.com',     # 发件人
        'to@example.com',          # 收件人（字符串或列表）
        '邮件主题',                 # 主题
        '邮件正文内容',             # 正文
    )
    return 'sent'
```

也可以显式传入连接参数（覆盖配置）：

```python
mail = Mail(host='smtp.example.com', port=587, user='u', password='p')
```

### 2. HTML 邮件

```python
await mail.send_mail(
    'from@test.com',
    'to@test.com',
    'HTML 邮件',
    '<b>Hello</b> <a href="https://example.com">link</a>',
    html=True,
)
```

### 3. 抄送与多收件人

```python
# 收件人支持逗号分隔字符串或列表
await mail.send_mail('from@test.com', 'a@test.com,b@test.com',
                     '主题', '正文', cc_='cc@test.com')

await mail.send_mail('from@test.com', ['a@test.com', 'b@test.com'],
                     '主题', '正文', cc_=['c@test.com', 'd@test.com'])
```

### 4. 附件

```python
await mail.send_mail(
    'from@test.com',
    'to@test.com',
    '带附件',
    '见附件',
    attachments=['/path/to/report.pdf', '/path/to/image.png'],
)
```

## EmailMessage 类

`EmailMessage` 用于构造 MIME 邮件对象，可直接操作或测试：

```python
from uliweb.mail import EmailMessage

msg = EmailMessage(
    from_='from@test.com',
    to_='to@test.com',
    subject='主题',
    message='正文',
    cc_=None,
    html=False,
    encoding='utf-8',
    attachments=None,
)

# 运行时追加附件
msg.attach('/path/to/file.txt')

# 或根据路径生成附件对象
att = msg.getAttachment('/path/to/file.txt')

# 序列化为邮件原始字符串
raw = str(msg)
```

`getAttachment()` 会根据文件 MIME 类型自动选择 MIMEText / MIMEImage / MIMEAudio / MIMEBase，非文本二进制默认使用 base64 编码。

## 异步说明

`Mail.send_mail()` 是异步方法，使用 `anyio.to_thread.run_sync` 将同步的 SMTP 操作放入线程池执行，因此在异步视图（`async def`）中调用不会阻塞事件循环。在同步视图或普通代码中，可通过 `anyio` / `asyncio` 运行：

```python
import asyncio

async def main():
    await Mail().send_mail('from@test.com', 'to@test.com', '主题', '正文')

asyncio.run(main())
```

## 测试

仓库提供对应单元测试 `test/test_mail.py`，覆盖：

- 基础消息构造与序列化
- HTML 内容
- 抄送字段
- 文本 / HTML / 图片 / 二进制附件类型识别
- `attach()` 与多附件
- Unicode 内容与文件名

运行测试：

```bash
pytest test/test_mail.py
```

## 依赖

仅依赖 Python 标准库（`smtplib`、`email`、`mimetypes`、`subprocess`）及 Uliweb3 核心（`anyio`）。
