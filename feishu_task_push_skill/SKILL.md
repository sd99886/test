# 飞书每日任务推送系统

自动从飞书项目、飞书任务、群消息三个数据源获取工作任务,智能过滤后推送给用户。

## 功能特性

- ✅ **多数据源整合**: 飞书项目 + 飞书任务 + 群消息 @mention
- ✅ **智能过滤**: 自动识别工作任务,过滤闲聊
- ✅ **open_id 匹配**: 不受用户改名影响
- ✅ **私聊通知**: 新任务实时推送给你
- ✅ **任务管理**: 命令行工具管理任务完成状态
- ✅ **多格式导出**: Markdown + JSON

## 使用前准备

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app) 创建应用
2. 记录 **App ID** 和 **App Secret**
3. 开通权限:
   - `im:chat:readonly` / `im:message:readonly` - 读取群消息
   - `task:task:read` - 读取任务
   - `im:message:send_as_bot` - 发送消息
4. 配置回调地址: `http://localhost:8899/callback`
5. **发布应用**(重要!)

### 2. 获取飞书项目 MCP Token

1. 访问 [飞书项目](https://project.feishu.cn)
2. 点击右上角头像 → 「开发者设置」
3. 复制 **MCP Token**

### 3. 安装依赖

```bash
pip install requests
```

### 4. 配置凭证

```bash
cp config.py.example config.py
# 编辑 config.py,填入你的配置
```

## 运行

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

## 配置项

| 配置项 | 位置 | 说明 |
|--------|------|------|
| `MCP_TOKEN` | config.py | 飞书项目 MCP Token |
| `APP_ID` / `APP_SECRET` | config.py | 飞书开放平台应用凭证 |
| `TARGET_OPEN_ID` | config.py | 你的飞书 open_id |
| `TARGET_GROUP_NAME` | config.py | 目标群名称 |

详细配置指南见 [TECHNICAL_DOC.md](TECHNICAL_DOC.md)

## 输出格式

### 终端表格

```
| 序号 | 完成 | 来源 | 标题 | 类型 | 状态 | 链接 |
|:----:|:----:|:----:|------|:----:|:----:|:----:|
| 1 | [ ] | 飞书项目 | 看板数据 | Epic | 需求调研中 | [打开](...) |
| 2 | [ ] | 群任务 | @初豪豪 将周报实现自动化 | 任务 | 进行中 | - |
```

### 导出文件

- `output/daily_tasks_YYYYMMDD.md` - Markdown 格式
- `output/daily_tasks_YYYYMMDD.json` - JSON 格式

## 常见问题

### Token 过期

user_access_token 有效期 2 小时,过期后会自动用 refresh_token 刷新。如果 refresh_token 也过期,需要重新授权。

### 机器人无法发送私聊

需要先在飞书中给应用机器人发一条消息建立会话。

### 群消息监听不到 @mention

1. 检查权限是否已发布
2. 检查 open_id 是否正确
3. 查看 monitor.py 日志确认消息格式

## 项目状态

**⚠️ 已暂停** - 详见 README.md

## 详细文档

[TECHNICAL_DOC.md](TECHNICAL_DOC.md) - 完整技术文档
