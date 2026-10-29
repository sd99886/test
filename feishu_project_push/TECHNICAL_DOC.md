# 飞书每日任务推送系统 - 技术文档

> **项目状态**: ⚠️ 已暂停  
> **最后更新**: 2026-10-14  
> **维护者**: Jenhao-初人豪

---

## 📋 目录

1. [项目概述](#项目概述)
2. [功能模块](#功能模块)
3. [快速开始](#快速开始)
4. [详细配置指南](#详细配置指南)
5. [文件说明](#文件说明)
6. [常见问题](#常见问题)
7. [项目暂停说明](#项目暂停说明)

---

## 项目概述

### 目标
自动从三个数据源获取工作任务,智能过滤后推送给用户:
1. **飞书项目** - Epic 视图中的工作项
2. **飞书任务** - 个人任务模块
3. **群消息** - 从指定群 @mention 中提取的工作任务

### 技术栈
- Python 3.8+
- 飞书开放平台 API (OAuth2)
- 飞书项目 MCP Server
- 本地 JSON 存储

---

## 功能模块

### 1. 飞书项目查询 (main.py)
通过 MCP Server 获取飞书项目 Epic 视图中的工作项。

**数据流**:
```
MCP Server → get_view_detail → 筛选负责人 → 输出表格
```

### 2. 飞书任务查询 (main.py)
通过 OAuth2 user_access_token 获取个人任务列表。

**数据流**:
```
OAuth2 授权 → user_access_token → /task/v2/tasks → 输出表格
```

### 3. 群消息监听 (monitor.py)
轮询指定群的消息,检测 @mention 并提取工作任务。

**数据流**:
```
轮询消息 → 检测 @mention → 智能过滤 → 提取任务 → 存储
```

### 4. 智能任务过滤 (extractor.py)
通过关键词规则判断消息是否是真正的工作任务,过滤闲聊。

**规则**:
- ✅ 工作关键词: 做/搞/处理/实现/搭建/开发/指标/看板/数据/需求等
- ❌ 负面词: 哈哈/收到/快干活/好的/明白等

### 5. 通知推送 (notifier.py)
通过飞书机器人私聊推送任务通知给用户。

### 6. 任务管理 (task_cli.py)
命令行工具,管理群任务(查看/标记完成/撤销)。

---

## 快速开始

### 前置条件
- Python 3.8+
- 飞书开放平台应用(已创建)
- 飞书项目 MCP Token

### 安装依赖
```bash
pip install requests
```

### 配置文件
复制配置模板并填写真实值:
```bash
cp config.py.example config.py
# 编辑 config.py,填入你的配置
```

### 运行
```bash
# 查询所有任务
python main.py

# 检查群消息中的新任务
python task_cli.py check

# 查看未完成任务
python task_cli.py list

# 标记任务完成
python task_cli.py done 1
```

---

## 详细配置指南

### 一、创建飞书应用

#### 1.1 创建应用
1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击「创建企业自建应用」
3. 填写应用名称(如"任务推送助手")和描述
4. 点击「创建」

#### 1.2 获取凭证
在「凭证与基础信息」页面记录:
- **App ID**: `cli_xxxxxxxxxxxxxxxx`
- **App Secret**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### 1.3 配置权限
在「权限管理」中申请以下权限:

**读取群消息**:
- `im:chat:readonly` - 获取单聊、群聊信息
- `im:message:readonly` - 读取单聊、群聊消息
- `im:chat` - 获取与更新单聊、群聊信息
- `im:message` - 获取与发送单聊、群聊消息

**读取任务**:
- `task:task:read` - 读取任务信息

**发送消息**:
- `im:message:send_as_bot` - 以应用的身份发消息

#### 1.4 配置回调地址
在「安全设置」→「重定向 URL」中添加:
```
http://localhost:8899/callback
```

#### 1.5 发布应用
点击「版本管理与发布」→「创建版本」→ 填写版本号和更新说明 → 「发布」

**注意**: 权限开通后必须发布新版本才能生效!

---

### 二、获取飞书项目 MCP Token

#### 2.1 获取 MCP Token
1. 访问 [飞书项目](https://project.feishu.cn)
2. 点击右上角头像 → 「开发者设置」
3. 复制 **MCP Token** (格式: `m-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

#### 2.2 获取 Project Key
1. 打开目标项目
2. 查看 URL: `https://project.feishu.cn/{simple_name}/...`
3. `{simple_name}` 就是 project_key (如 `cupshe_rdc`)

#### 2.3 获取 View ID
1. 打开 Epic 视图
2. 查看 URL: `...?view=xxxxxxxxx`
3. `view=` 后面的就是 view_id

---

### 三、配置 OAuth2 授权

#### 3.1 首次授权
运行 `main.py` 时,如果 token 过期会自动弹出浏览器:
1. 浏览器打开飞书授权页面
2. 登录你的飞书账号
3. 点击「授权」
4. 自动跳转回 `http://localhost:8899/callback?code=xxx`
5. 脚本自动用 code 换取 user_access_token 并缓存

#### 3.2 Token 刷新
- user_access_token 有效期 2 小时
- 过期后会自动用 refresh_token 刷新(无需重新授权)
- 如果 refresh_token 也过期,需要重新授权

---

### 四、配置群消息监听

#### 4.1 获取目标群的 chat_id
运行以下命令获取所有群列表:
```python
import requests
from config import APP_ID, APP_SECRET

# 获取 tenant_access_token
r = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
                  json={'app_id': APP_ID, 'app_secret': APP_SECRET})
token = r.json()['tenant_access_token']

# 获取群列表
r = requests.get('https://open.feishu.cn/open-apis/im/v1/chats',
                 headers={'Authorization': f'Bearer {token}'})
for chat in r.json()['data']['items']:
    print(f"{chat['name']}: {chat['chat_id']}")
```

#### 4.2 获取用户的 open_id
```python
import requests
from config import APP_ID, APP_SECRET

r = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
                  json={'app_id': APP_ID, 'app_secret': APP_SECRET})
token = r.json()['tenant_access_token']

# 用 user_access_token 获取用户信息
r = requests.get('https://open.feishu.cn/open-apis/authen/v1/user_info',
                 headers={'Authorization': f'Bearer {user_access_token}'})
print(f"open_id: {r.json()['data']['open_id']}")
```

#### 4.3 配置 config.py
```python
# 目标群名称
TARGET_GROUP_NAME = "产品/供应链中心数据内部沟通群"

# 目标用户的 open_id (用于 @mention 检测)
TARGET_OPEN_ID = "ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 备用:文本回退匹配这些名字
MENTION_NAMES = ["初豪豪", "Jenhao", "初人豪"]
```

---

### 五、配置通知推送

#### 5.1 获取机器人 Webhook
**方法一:通过群设置获取**
1. 打开目标群聊
2. 点击右上角「...」→「群机器人」
3. 找到你的机器人 → 点击「设置」
4. 复制 **Webhook 地址** (格式: `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx`)

**方法二:通过飞书开放平台获取**
1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 进入你的应用 → 「机器人」
3. 点击「添加机器人」→ 选择目标群
4. 添加成功后会显示 Webhook 地址

**方法三:使用应用机器人私聊(推荐)**
不需要 Webhook,直接通过应用机器人发私聊消息:
```python
# config.py
NOTIFY_USER_OPEN_ID = "ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 你的 open_id
```

#### 5.2 测试通知
```bash
python -c "from notifier import Notifier; from config import *; n = Notifier(APP_ID, APP_SECRET, user_open_id=NOTIFY_USER_OPEN_ID); print(n.send_text('测试消息'))"
```

---

## 文件说明

```
feishu_project_push/
├── config.py              # 配置文件(敏感信息,不提交)
├── config.py.example      # 配置模板(脱敏版本)
├── main.py                # 主脚本(飞书项目+任务查询)
├── monitor.py             # 群消息监听
├── extractor.py           # 任务提取与智能过滤
├── notifier.py            # 通知推送
├── task_store.py          # 任务存储(JSON)
├── task_cli.py            # 命令行任务管理工具
├── requirements.txt       # 依赖列表
├── .gitignore            # Git 忽略配置
├── README.md             # 项目说明
└── output/               # 导出文件目录
    ├── daily_tasks_*.md  # Markdown 格式任务列表
    └── daily_tasks_*.json # JSON 格式任务列表
```

---

## 常见问题

### Q1: 飞书项目查询失败 "ProjectNotFound"
**原因**: View ID 或 Project Key 不正确  
**解决**: 
1. 检查 config.py 中的 VIEW_ID 和 PROJECT_KEY
2. 确保 MCP Token 有效
3. 在飞书项目中确认视图存在

### Q2: 飞书任务 Token 过期
**原因**: user_access_token 有效期 2 小时  
**解决**: 
1. 自动刷新:脚本会自动用 refresh_token 刷新
2. 手动刷新:删除 `.user_task_token_cache.json`,重新运行 `main.py`

### Q3: 群消息监听不到 @mention
**原因**: 
1. 权限未发布
2. open_id 不匹配
3. 系统消息被误识别

**解决**:
1. 在飞书开放平台发布应用新版本
2. 检查 TARGET_OPEN_ID 是否正确
3. 查看 monitor.py 日志确认消息格式

### Q4: 机器人无法发送私聊
**原因**: 用户没有先给机器人发消息建立会话  
**解决**: 
1. 在飞书中搜索应用机器人
2. 给机器人发一条消息(如"hi")
3. 再次尝试发送通知

### Q5: 智能过滤误判
**原因**: 关键词规则不够完善  
**解决**: 
1. 编辑 `extractor.py` 中的 `TASK_KEYWORDS` 和 `NEGATIVE_KEYWORDS`
2. 或者配置 AI_API_KEY 使用 LLM 智能判断

---

## 项目暂停说明

### 暂停原因

1. **飞书项目 View ID 问题**
   - 错误: `ProjectNotFound: project: HUfbjwsvR not found`
   - 原因: View ID 格式不正确或已失效
   - 状态: 待排查

2. **多维表格同步失败**
   - 错误: 字段类型映射复杂(Date/MultiSelect/SingleSelect)
   - 原因: 飞书 API 字段类型与预期不符
   - 状态: 已放弃(改用终端输出)

3. **前端交互界面放弃**
   - 原因: 用户更习惯终端操作
   - 状态: 已删除相关文件

### 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 飞书项目查询 | ⚠️ 待修复 | View ID 问题 |
| 飞书任务查询 | ✅ 正常 | 需要重新授权 |
| 群消息监听 | ✅ 正常 | 3 条任务已识别 |
| 智能过滤 | ✅ 正常 | 成功过滤闲聊 |
| 私聊通知 | ✅ 正常 | 已测试通过 |
| 定时任务 | ❌ 已删除 | 用户要求停止 |

### 后续计划

1. **修复飞书项目查询**: 重新获取正确的 View ID
2. **优化智能过滤**: 根据实际使用情况调整关键词规则
3. **探索其他推送方式**: 如飞书文档、邮件等

---

## 附录

### A. 飞书 API 文档
- [飞书开放平台](https://open.feishu.cn/document)
- [飞书项目 API](https://project.feishu.cn/openapi)
- [飞书任务 API](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/task-v2/task/overview)

### B. 相关资源
- [飞书 MCP Server](https://project.feishu.cn/mcp_server/v1)
- [飞书机器人 Webhook](https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN)

### C. 联系方式
如有问题,请联系: Jenhao-初人豪

---

**最后更新**: 2026-10-14  
**文档版本**: v1.0
