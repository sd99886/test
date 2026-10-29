# 飞书每日任务推送系统

> **⚠️ 项目状态: 已暂停**  
> 详见 [项目暂停说明](#项目暂停说明)

---

## 📋 功能概述

自动从三个数据源获取工作任务,智能过滤后推送给用户:

1. **飞书项目** - 从 Epic 视图获取工作项
2. **飞书任务** - 获取个人任务列表
3. **群消息** - 监听 @mention 并提取工作任务

### 核心特性

- ✅ **智能过滤**: 自动识别工作任务,过滤闲聊(如"快干活"、"哈哈")
- ✅ **open_id 匹配**: 不受用户改名影响
- ✅ **私聊通知**: 新任务实时推送给你
- ✅ **任务管理**: 命令行工具管理任务完成状态
- ✅ **多格式导出**: Markdown + JSON

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests
```

### 2. 配置凭证

```bash
cp config.py.example config.py
# 编辑 config.py,填入你的配置
```

**必填配置**:
- `MCP_TOKEN` - 飞书项目 MCP Token
- `APP_ID` / `APP_SECRET` - 飞书开放平台应用凭证
- `TARGET_OPEN_ID` - 你的飞书 open_id

详细配置指南见 [TECHNICAL_DOC.md](TECHNICAL_DOC.md)

### 3. 运行

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

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | 主脚本(飞书项目+任务查询+每日推送) |
| `monitor.py` | 群消息监听(@mention 检测) |
| `extractor.py` | 任务提取与智能过滤 |
| `notifier.py` | 通知推送(私聊/Webhook) |
| `task_store.py` | 任务存储(JSON) |
| `task_cli.py` | 命令行任务管理工具 |
| `config.py` | 配置文件(敏感,不提交) |
| `config.py.example` | 配置模板(脱敏版本) |
| `TECHNICAL_DOC.md` | 详细技术文档 |

---

## 🔧 配置指南

### 一、创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app) 创建应用
2. 记录 **App ID** 和 **App Secret**
3. 开通权限:
   - `im:chat:readonly` / `im:message:readonly` - 读取群消息
   - `task:task:read` - 读取任务
   - `im:message:send_as_bot` - 发送消息
4. 配置回调地址: `http://localhost:8899/callback`
5. **发布应用**(重要!)

### 二、获取飞书项目 MCP Token

1. 访问 [飞书项目](https://project.feishu.cn)
2. 点击右上角头像 → 「开发者设置」
3. 复制 **MCP Token**

### 三、获取 open_id

运行以下脚本获取你的 open_id:

```python
import requests
token = "your_user_access_token"
r = requests.get('https://open.feishu.cn/open-apis/authen/v1/user_info',
                 headers={'Authorization': f'Bearer {token}'})
print(f"open_id: {r.json()['data']['open_id']}")
```

详细配置步骤见 [TECHNICAL_DOC.md](TECHNICAL_DOC.md)

---

## 📊 输出示例

### 终端输出

```
============================================================
  飞书每日任务推送
  日期: 2026-10-14
  负责人: Jenhao-初人豪
============================================================

### 进行中

| 序号 | 完成 | 来源 | 标题 | 类型 | 状态 | 链接 |
|:----:|:----:|:----:|------|:----:|:----:|:----:|
| 1 | [ ] | 飞书项目 | 看板数据 | Epic | 需求调研中 | [打开](...) |
| 2 | [ ] | 飞书任务 | 本月新增指标 | 任务 | 进行中 | [打开](...) |
| 3 | [ ] | 群任务 | @初豪豪 将周报实现自动化 | 任务 | 进行中 | - |

### [已完成]

| 序号 | 完成 | 来源 | 标题 | 完成时间 |
|:----:|:----:|:----:|------|:--------:|
| 1 | [x] | 群任务 | @初豪豪 退件率指标... | 2026-10-14 11:27 |
```

### 导出文件

- `output/daily_tasks_20261014.md` - Markdown 格式
- `output/daily_tasks_20261014.json` - JSON 格式

---

## 🛠️ 命令行工具

### task_cli.py

```bash
# 检查群消息中的新 @mention
python task_cli.py check

# 查看未完成任务
python task_cli.py list

# 查看所有任务(含已完成)
python task_cli.py list --all

# 标记任务完成
python task_cli.py done 1

# 取消完成
python task_cli.py undo 1
```

---

## 项目暂停说明

### 暂停原因

1. **飞书项目 View ID 问题**
   - 错误: `ProjectNotFound: project: HUfbjwsvR not found`
   - 原因: View ID 格式不正确或已失效
   - 状态: 待排查

2. **多维表格同步失败**
   - 错误: 字段类型映射复杂
   - 原因: 飞书 API 字段类型与预期不符
   - 状态: 已放弃

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

1. 修复飞书项目查询(重新获取 View ID)
2. 优化智能过滤规则
3. 探索其他推送方式

---

## 📚 详细文档

完整的技术文档、配置指南、API 说明见:

**[TECHNICAL_DOC.md](TECHNICAL_DOC.md)**

---

## 🤖 机器人 Webhook 获取方式

### 方法一:通过群设置获取

1. 打开目标群聊
2. 点击右上角「...」→「群机器人」
3. 找到你的机器人 → 点击「设置」
4. 复制 **Webhook 地址**

格式: `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### 方法二:通过飞书开放平台获取

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 进入你的应用 → 「机器人」
3. 点击「添加机器人」→ 选择目标群
4. 添加成功后会显示 Webhook 地址

### 方法三:使用应用机器人私聊(推荐)

不需要 Webhook,直接通过应用机器人发私聊消息:

```python
# config.py
NOTIFY_USER_OPEN_ID = "ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 你的 open_id
```

**注意**: 需要先在飞书中给机器人发一条消息建立会话。

---

## 📝 License

MIT License

---

**最后更新**: 2026-10-14  
**维护者**: Jenhao-初人豪
