"""
Gunicorn 配置文件
用于生产环境部署 Flask 应用
"""

# 绑定地址和端口
bind = "0.0.0.0:5000"

# Worker 进程数（建议 CPU核心数 * 2 + 1）
workers = 4

# Worker 类型
worker_class = "sync"

# 每个 worker 处理的请求数后重启（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 超时设置（秒）
timeout = 120
keepalive = 5

# 日志配置
accesslog = "/opt/data-api/logs/access.log"
errorlog = "/opt/data-api/logs/error.log"
loglevel = "info"

# 进程命名
proc_name = "data-api"

# 预加载应用（加快启动速度）
preload_app = True

# Graceful timeout
graceful_timeout = 30
