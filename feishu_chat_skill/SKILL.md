---
name: feishu-chat-reader
description: 读取飞书指定群聊的消息记录，支持 OAuth2 授权、Token 缓存、合并转发消息展开，导出为 JSON + Markdown 表格。当用户需要读取飞书群聊消息、导出聊天记录、分析群聊内容时使用。
---

# 飞书聊天消息读取器

读取飞书指定群聊的消息记录，支持 OAuth2 用户授权、Token 本地缓存、合并转发消息自动展开，导出为 JSON（原始数据）+ Markdown（清洗后表格）。

## 使用前准备

### 1. 创建飞书应用
1. 访问 [飞书开放平台](https://open.feishu.cn/app) 创建应用
2. 记录 **App ID** 和 **App Secret**

### 2. 配置权限
在应用「权限管理」中申请以下权限：
- `im:chat` — 获取与更新单聊、群聊信息
- `im:chat:readonly` — 获取单聊、群聊信息
- `im:message` — 获取与发送单聊、群聊消息
- `im:message:readonly` — 读取消息

### 3. 配置回调地址
在应用「安全设置」中添加重定向 URL：
```
http://localhost:8899/callback
```

### 4. 发布应用
权限开通后必须**发布新版本**才能生效。

### 5. 安装依赖
```bash
pip install -r requirements.txt
```

### 6. 配置凭证
```bash
cp config.py.example config.py
# 编辑 config.py，填入 APP_ID 和 APP_SECRET
```

### 7. 配置目标群
编辑 `feishu_chat_reader.py`，修改 `TARGET_GROUPS` 为你要读取的群名（必须与飞书中群名完全一致）：
```python
TARGET_GROUPS = [
    "你的目标群名",
]
```

## 运行

```bash
python feishu_chat_reader.py
```

首次运行会：
1. 自动打开浏览器，跳转飞书授权页面
2. 用户登录并同意授权
3. 自动获取 Token 并缓存到 `.token_cache.json`
4. 读取目标群最近 7 天的消息
5. 导出为 `feishu_chats_<时间戳>.json` 和 `feishu_chats_<时间戳>.md`

后续运行会自动复用缓存的 Token（有效期 2 小时），无需重复授权。

## 配置项

| 配置项 | 位置 | 说明 |
|--------|------|------|
| `APP_ID` | config.py | 飞书应用 App ID |
| `APP_SECRET` | config.py | 飞书应用 App Secret |
| `REDIRECT_URI` | config.py | OAuth 回调地址 |
| `LOCAL_PORT` | config.py | 本地回调服务端口 |
| `TARGET_GROUPS` | feishu_chat_reader.py | 要读取的群名列表 |
| `READ_DAYS` | feishu_chat_reader.py | 读取最近 N 天的消息 |

## 输出格式

### JSON（原始数据）
包含完整的消息原始数据，包括消息 ID、发送者、时间戳、消息体等。合并转发消息的 `_expanded` 字段包含所有子消息详情。

### Markdown（清洗后表格）
| 序号 | 时间 | 类型 | 发送者 | 内容 |
|------|------|------|--------|------|
| 1 | 10-13 13:56 | text | ou_xxx | 消息内容 |

支持的消息类型：text、post（富文本）、image、file、audio、media、sticker、interactive、system、merge_forward。

## 常见问题

### 错误码 20029（重定向 URL 有误）
回调地址未在飞书应用「安全设置」中配置，添加 `http://localhost:8899/callback` 后重试。

### 返回 0 个群聊
- 检查权限是否已发布生效
- 确认应用权限包含 `im:chat:readonly`
- 群名必须与飞书中完全一致（区分大小写和空格）

### Token 过期
Token 缓存有效期 2 小时，过期后会自动重新弹出浏览器授权。
