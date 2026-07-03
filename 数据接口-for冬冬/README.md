# 数据接口-for冬冬

## 📋 项目定位

**纯数据API服务**，供外部AI平台调用MaxCompute数据。

### 业务场景

```
─────────────────┐         ┌──────────────────┐
│   数分侧          │         │   业务方AI平台     │
│                  │         │                  │
│  1. 编写SQL      │         │  1. 输入问题      │
│  2. 保存为接口    │───────▶│  2. 调用数据接口   │
│  3. 部署API服务   │ HTTP   │  3. AI分析返回结果 │
│                  │         │                  │
└─────────────────┘         └──────────────────┘
```

---

## 🚀 快速启动

### 本地开发模式

```bash
cd 数据接口-for冬冬
python app.py
```

访问：
- **API文档首页**: http://localhost:5000/
- **数分管理后台**: http://localhost:5000/admin
- **接口列表**: http://localhost:5000/api/queries

---

### 无服务器方案（推荐临时使用）

**场景：** 没有服务器，但需要让外部AI平台（如Manus AI）调用接口

#### 方案1：ngrok 内网穿透（最简单）

1. **安装 ngrok**
   - 访问 https://ngrok.com/download 下载 Windows 版
   - 解压后把 `ngrok.exe` 放到任意目录

2. **注册账号获取 token**
   - 访问 https://ngrok.com 注册（可用GitHub登录）
   - 获取 authtoken，执行：
   ```bash
   ngrok config add-authtoken 你的token
   ```

3. **启动服务**
   ```bash
   # 终端1：启动Flask服务
   python app.py
   
   # 终端2：启动ngrok
   ngrok http 5000
   ```

4. **获取公网地址**
   - ngrok 会显示类似：`https://xxxx-xxx.ngrok-free.app → http://localhost:5000`
   - 把这个地址给 Manus AI 即可调用

5. **调用示例**
   ```python
   import requests
   
   # 使用ngrok提供的地址
   headers = {'X-API-Key': 'cupshe-data-2026'}
   response = requests.get('https://xxxx-xxx.ngrok-free.app/api/query/sales_report', headers=headers)
   data = response.json()
   ```

⚠️ **注意：**
- 免费版 ngrok 每次重启地址会变
- 关闭电脑后服务中断
- 适合临时测试，不适合长期生产

#### 方案2：Cloudflare Tunnel（更稳定）

1. **安装 cloudflared**
   ```bash
   # Windows
   winget install Cloudflare.cloudflared
   ```

2. **创建隧道**
   ```bash
   # 登录
   cloudflared tunnel login
   
   # 创建隧道
   cloudflared tunnel create my-api-tunnel
   
   # 配置路由
   cloudflared tunnel route dns my-api-tunnel your-domain.com
   ```

3. **启动隧道**
   ```bash
   cloudflared tunnel run --url http://localhost:5000 my-api-tunnel
   ```

4. **访问**
   - 通过 `https://your-domain.com/api/query/sales_report` 访问
   - 更稳定，支持自定义域名

---

### 生产环境部署（有服务器时）

#### 方式1：Gunicorn + Nginx（推荐）

```bash
# 安装 gunicorn
pip install gunicorn

# 启动服务（4个worker进程）
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 或使用 systemd 管理服务
sudo systemctl start data-api
```

#### 方式2：Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
# 构建镜像
docker build -t data-api .

# 运行容器
docker run -p 5000:5000 \
  -e ODPS_ACCESS_ID=xxx \
  -e ODPS_ACCESS_KEY=xxx \
  data-api
```

---

## 📝 使用流程

### 数分视角（编写SQL）

1. 访问管理后台：http://your-server.com/admin
2. 点击「+ 新建查询」或选择已有查询编辑
3. 编写SQL语句（如销售报表、库存查询等）
4. 点击「保存并发布」→ 自动生成接口 `/api/query/{名称}`
5. 复制接口URL提供给业务方

### 业务方视角（调用接口）

业务方在自己的AI平台中调用数据接口：

**Python示例：**
```python
import requests

# 调用数据接口
response = requests.get('http://your-server.com/api/query/sales_report')
data = response.json()

if data['success']:
    records = data['data']      # 数据列表
    columns = data['columns']   # 字段名
    row_count = data['row_count']  # 行数
    
    # 将数据传给AI进行分析
    ai_analyze(records, columns)
```

**JavaScript示例：**
```javascript
fetch('http://your-server.com/api/query/sales_report')
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      const records = data.data;
      // 调用AI分析
      aiAnalyze(records);
    }
  });
```

---

## 🔧 API 参考

### 列出所有接口

```
GET /api/queries
```

响应：
```json
{
  "success": true,
  "queries": [
    {
      "name": "sales_report",
      "description": "销售报表查询",
      "api_url": "/api/query/sales_report",
      "full_url": "http://your-server.com/api/query/sales_report"
    }
  ]
}
```

### 执行指定查询

```
GET /api/query/{name}?limit=100
```

参数：
- `limit`（可选）：最大返回行数，默认1000

响应：
```json
{
  "success": true,
  "data": [
    {"字段1": "值1", "字段2": "值2"},
    {"字段1": "值3", "字段2": "值4"}
  ],
  "columns": ["字段1", "字段2"],
  "row_count": 100,
  "exec_time": 5.23,
  "query_time": "2026-07-03 16:30:00"
}
```

### 执行自定义SQL（临时测试）

```
POST /api/query
Content-Type: application/json

{
  "sql": "SELECT * FROM table LIMIT 10",
  "limit": 100
}
```

---

## ⚙️ 配置说明

编辑 `config.py`：

```python
# ============ MaxCompute 连接配置 ============
ODPS_ACCESS_ID = '你的AccessKey ID'
ODPS_ACCESS_KEY = '你的AccessKey Secret'
ODPS_PROJECT = "cupshe_bigdata_ads"
ODPS_ENDPOINT = "https://service.eu-central-1.maxcompute.aliyun.com/api"

# ============ API服务配置 ============
API_HOST = "0.0.0.0"      # 监听地址
API_PORT = 5000            # 监听端口
MAX_RESULT_ROWS = 1000     # 单次查询最大返回行数
SQL_DIR = "sql"            # SQL文件目录
```

️ **安全提示：**
- `config.py` 已加入 `.gitignore`，不会提交到Git
- 生产环境建议使用环境变量或密钥管理服务

---

## 📁 项目结构

```
数据接口-for冬冬/
├── app.py              # 核心服务（Flask应用）
├── config.py           # 配置文件（已gitignore）
├── config.py.example   # 配置模板
├── requirements.txt    # Python依赖
├── README.md           # 本文档
├── sql/                # SQL文件目录
│   ├── query.sql       # 示例SQL
│   └── ...             # 数分编写的其他SQL
└── templates/
    ├── index.html      # API文档首页
    └── admin.html      # 数分管理后台
```

---

## 🛠️ 技术栈

- **后端框架：** Flask 3.0
- **数据库连接：** pyodps（MaxCompute SDK）
- **数据处理：** pandas
- **跨域支持：** flask-cors
- **前端：** 原生 HTML/CSS/JS

---

## ❓ 常见问题

### Q1: 页面显示 "加载失败"？

**原因：** Flask 服务未启动

**解决：**
```bash
python app.py
```

### Q2: MaxCompute 连接失败？

检查 `config.py` 中的 AccessKey 是否正确，确认有访问权限。

### Q3: 如何限制接口访问权限？

生产环境建议：
1. 使用 Nginx 反向代理 + IP白名单
2. 添加 API Key 认证（在 `app.py` 中添加装饰器）
3. 使用 HTTPS 加密传输

### Q4: 查询超时怎么办？

调整 `config.py` 中的 `MAX_RESULT_ROWS`，或优化SQL查询性能。

---

## 📞 技术支持

如有问题，请联系数分团队或查看 Flask 日志输出。
