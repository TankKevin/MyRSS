# MyRSS

Python 后端脚本：每天 8 点抓取指定 RSS，整理成邮件并发送给收件人。

## 快速开始
1) 创建虚拟环境并安装依赖
```bash
cd /Users/applekvt/Projects_KVT/MyRSS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) 配置环境变量（可写入 `.env`，程序会自动读取；或直接 `export`）
```
RSS_FEED_URL=https://example.com/feed.xml
RSS_VERIFY_SSL=true                # 如源站证书异常可设为 false（不安全）
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_user        # 可选，若服务器不需要认证可留空
SMTP_PASSWORD=your_smtp_password    # 可选
SMTP_STARTTLS=true                  # 是否开启 STARTTLS，默认 true
EMAIL_FROM=notify@example.com
EMAIL_TO=user1@example.com,user2@example.com
EMAIL_SUBJECT=Daily RSS Digest      # 可选，默认值
ENTRY_LIMIT=20                      # 可选，限制抓取条数
```

3) 手动运行一次验证
```bash
# 推荐：以模块方式运行（避免相对导入问题）
python -m rss_mailer.runner

# 或直接运行文件
python rss_mailer/runner.py
```

### 自定义邮件模板
- HTML 模板位于 `rss_mailer/templates/email.html`（Jinja2），可按需修改样式/字段。
- 邮件同时包含纯文本备份，防止部分客户端不渲染 HTML。
- 默认仅发送“前一天 (UTC)”发布的 RSS 条目，若无匹配会提示为空。

## Docker 部署
1) 构建镜像
```bash
docker build -t myrss:latest .
```

2) 在服务器上准备 `.env`（可复用 `.env.example`）。运行一次测试：
```bash
docker run --rm --env-file .env myrss:latest
```

3) 定时任务（以服务器时区的 8:00 为例，在宿主机 `crontab -e`）：
```
0 8 * * * docker run --rm --env-file /path/to/.env myrss:latest >> /var/log/myrss.log 2>&1
```
- 如需和宿主机时区保持一致，可额外挂载 `-v /etc/localtime:/etc/localtime:ro`。

## 每天早上 8 点定时运行
在本机 `crontab -e` 添加（假设项目路径为 `/Users/applekvt/Projects_KVT/MyRSS` 且使用上面的虚拟环境）：
```
0 8 * * * cd /Users/applekvt/Projects_KVT/MyRSS && . .venv/bin/activate && python -m rss_mailer.runner >> cron.log 2>&1
```
说明：`cron.log` 用于记录运行日志，方便排查。

## 代码结构
- `rss_mailer/config.py`：读取和校验环境变量。
- `rss_mailer/rss_fetcher.py`：抓取并解析 RSS（使用 feedparser）。
- `rss_mailer/email_sender.py`：整理邮件正文并通过 SMTP 发送。
- `rss_mailer/runner.py`：入口程序，串联配置、抓取、邮件发送。
- `requirements.txt`：Python 依赖。

## 其他说明
- 邮件正文为纯文本格式，包含标题、发布时间（UTC）与链接。
- 如使用 Gmail，可将 `SMTP_HOST=smtp.gmail.com`，`SMTP_PORT=587`，并在账号设置中启用应用专用密码。
- 如果你的 SMTP 服务器要求 SSL（而非 STARTTLS），可将 `SMTP_STARTTLS=false` 并在 `SMTP_PORT` 设置为对应端口（例如 465），同时确保服务器接受明文连接或自行调整代码使用 `smtplib.SMTP_SSL`。
