"""
飞书聊天消息读取模块
支持按指定群名读取消息记录，不会读取其他群或私聊。
使用 OAuth2 user_access_token 方式，读取当前授权用户的数据。

使用前准备：
1. 在 https://open.feishu.cn/app 创建应用
2. 在「权限管理」中申请以下权限：
   - im:chat              (获取与更新单聊、群聊信息)
   - im:chat:readonly     (获取单聊、群聊信息)
   - im:message           (获取与发送单聊、群聊消息)
   - im:message:readonly  (读取消息)
3. 在「安全设置」中添加重定向 URL：http://localhost:8899/callback
4. 发布应用版本（权限需要发布后生效）
"""

import json
import os
import time
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, quote
from datetime import datetime

import requests

from config import APP_ID, APP_SECRET, REDIRECT_URI, LOCAL_PORT

# Token 缓存文件路径
TOKEN_CACHE_FILE = os.path.join(os.path.dirname(__file__), ".token_cache.json")

# OAuth 显式请求的用户级 scope（缺此参数时新开通的用户权限不会进入 token，
# 会导致建文档/读群聊报 99991679）：覆盖发布报告与读群聊全链路。
OAUTH_SCOPES = (
    "docx:document docx:document:create "
    "im:chat:readonly im:message:readonly "
    "sheets:spreadsheet drive:drive"
)


# ==================== OAuth2 授权 ====================

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """本地 HTTP 服务，用于接收飞书 OAuth 回调"""
    auth_code = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            OAuthCallbackHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("授权成功！请回到终端查看结果。".encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code parameter")

    def log_message(self, format, *args):
        pass  # 静默日志


def get_user_access_token():
    """
    获取 user_access_token（带本地缓存，有效期内自动复用）。
    缓存过期或不存在时才走 OAuth2 授权流程。
    """
    # 1. 尝试从缓存读取
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            cached_token = cache.get("access_token", "")
            expires_at = cache.get("expires_at", 0)
            # 提前5分钟过期，避免边界问题
            if cached_token and time.time() < expires_at - 300:
                remaining = int(expires_at - time.time())
                print(f"[Token 缓存] 使用本地缓存，剩余有效期 {remaining // 60} 分钟")
                return cached_token
            else:
                print("[Token 缓存] 已过期，重新授权")
        except Exception:
            print("[Token 缓存] 读取失败，重新授权")

    # 2. 走 OAuth2 授权流程
    return _do_oauth_authorization()


def _do_oauth_authorization():
    """执行 OAuth2 授权流程，获取并缓存 user_access_token"""
    auth_url = (
        "https://open.feishu.cn/open-apis/authen/v1/authorize"
        f"?app_id={APP_ID}"
        f"&redirect_uri={quote(REDIRECT_URI, safe='')}"
        f"&scope={quote(OAUTH_SCOPES)}"
        "&state=chat_reader"
    )

    print("=" * 60)
    print("飞书 OAuth2 授权")
    print("=" * 60)
    print(f"\n正在打开浏览器，请访问以下链接登录授权：")
    print(f"\n  {auth_url}\n")
    print("授权完成后，程序会自动获取 token...\n")

    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", LOCAL_PORT), OAuthCallbackHandler)
    server.timeout = 120
    OAuthCallbackHandler.auth_code = None

    def handle_request():
        try:
            server.handle_request()
        except Exception:
            pass

    thread = threading.Thread(target=handle_request)
    thread.start()
    thread.join(timeout=120)
    server.server_close()

    code = OAuthCallbackHandler.auth_code
    if not code:
        raise Exception("授权超时或失败，未获取到授权码")

    print(f"获取到授权码: {code[:8]}...")

    # 获取 app_access_token
    app_token_resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
    )
    app_token_data = app_token_resp.json()
    if app_token_data.get("code") != 0:
        raise Exception(f"获取 app_access_token 失败: {app_token_data}")
    app_access_token = app_token_data["app_access_token"]

    # 用 code 换取 user_access_token
    url = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {app_access_token}",
    }
    resp = requests.post(url, headers=headers, json={
        "grant_type": "authorization_code",
        "code": code,
    })
    data = resp.json()

    if data.get("code") != 0:
        raise Exception(f"获取 user_access_token 失败: {data}")

    token_data = data["data"]
    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 7200)
    print(f"\n授权成功！用户: {token_data.get('name', '未知')}")
    print(f"Token 有效期: {expires_in} 秒")

    # 缓存到本地文件
    cache = {
        "access_token": access_token,
        "expires_at": time.time() + expires_in,
        "user_name": token_data.get("name", ""),
    }
    with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"Token 已缓存到: {TOKEN_CACHE_FILE}")

    return access_token


# ==================== API 请求封装 ====================

class FeishuChatReader:
    """飞书聊天消息读取器"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def _get(self, path, params=None):
        """发送 GET 请求（带调试信息）"""
        url = f"{self.BASE_URL}{path}"
        resp = requests.get(url, headers=self.headers, params=params)
        data = resp.json()
        if data.get("code") != 0:
            print(f"[API 错误] {path}: code={data.get('code')}, msg={data.get('msg')}")
            print(f"  完整响应: {json.dumps(data, ensure_ascii=False)}")
            return None
        return data.get("data", {})

    # ---------- 聊天列表 ----------

    def list_all_chats(self, page_size=50):
        """
        获取用户所在的所有聊天（群聊 + 私聊），自动翻页
        :return: 聊天列表，每个元素包含 chat_id, name, chat_type 等
        """
        chats = []
        page_token = None

        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            data = self._get("/im/v1/chats", params)
            if data is None:
                print("  [调试] API 返回 None，可能是权限不足或参数问题")
                break

            items = data.get("items", [])
            chats.extend(items)

            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

        return chats

    def list_group_chats(self):
        """只获取群聊（自动翻页）"""
        chats = []
        page_token = None

        while True:
            params = {"page_size": 50, "chat_type": "group"}
            if page_token:
                params["page_token"] = page_token

            data = self._get("/im/v1/chats", params)
            if data is None:
                break

            items = data.get("items", [])
            chats.extend(items)

            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

        return chats

    def list_p2p_chats(self):
        """只获取私聊（单聊）"""
        return [c for c in self.list_all_chats() if c.get("chat_type") == "p2p"]

    # ---------- 消息读取 ----------

    def get_messages(self, chat_id, page_size=50, start_time=None, end_time=None):
        """
        读取指定聊天的消息
        :param chat_id: 聊天 ID
        :param page_size: 每页消息数，最大50
        :param start_time: 起始时间戳（秒），如 "1672502400"
        :param end_time: 结束时间戳（秒）
        :return: 消息列表
        """
        messages = []
        page_token = None

        while True:
            params = {
                "container_id_type": "chat",
                "container_id": chat_id,
                "page_size": page_size,
                "sort_type": "ByCreateTimeAsc",  # 按时间升序
            }
            if page_token:
                params["page_token"] = page_token
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time

            data = self._get("/im/v1/messages", params)
            if not data:
                break

            items = data.get("items", [])
            messages.extend(items)

            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

        return messages

    def get_message_detail(self, message_id):
        """
        获取单条消息的详情（用于读取合并转发等特殊类型消息的实际内容）
        :param message_id: 消息 ID
        :return: 消息详情 dict 或 None
        """
        data = self._get(f"/im/v1/messages/{message_id}")
        if data:
            # 合并转发消息返回的是 items 列表，普通消息返回 message 字段
            if "items" in data:
                return {"items": data["items"]}
            return data.get("message", data)
        return None

    def get_recent_messages(self, chat_id, days=7):
        """
        读取最近 N 天的消息（自动展开合并转发消息内容）
        :param chat_id: 聊天 ID
        :param days: 最近天数，默认7天
        """
        start_ts = str(int(time.time()) - days * 86400)
        messages = self.get_messages(chat_id, start_time=start_ts)

        # 展开合并转发消息
        for msg in messages:
            if msg.get("msg_type") == "merge_forward":
                detail = self.get_message_detail(msg.get("message_id", ""))
                if detail:
                    msg["_expanded"] = detail
                time.sleep(0.2)  # 避免频率限制

        return messages

    # ---------- 用户信息 ----------

    def get_user_info(self):
        """获取当前授权用户的基本信息"""
        url = "https://open.feishu.cn/open-apis/authen/v1/user_info"
        resp = requests.get(url, headers=self.headers)
        data = resp.json()
        if data.get("code") != 0:
            print(f"[API 错误] 获取用户信息失败: {data}")
            return None
        return data.get("data", {})


# ==================== 消息格式化 ====================

def format_message(msg):
    """将消息格式化为可读文本"""
    sender = msg.get("sender", {})
    sender_id = sender.get("id", "未知")
    sender_type = sender.get("sender_type", "")

    # 消息时间
    create_time = msg.get("create_time", "")
    if create_time:
        try:
            dt = datetime.fromtimestamp(int(create_time) / 1000)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            time_str = create_time
    else:
        time_str = "未知时间"

    # 消息类型和内容
    msg_type = msg.get("msg_type", "unknown")
    body = msg.get("body", {})
    content = body.get("content", "")

    # 尝试解析 JSON 内容
    try:
        content_obj = json.loads(content)
        if msg_type == "text":
            content_text = content_obj.get("text", "")
        elif msg_type == "post":
            # 富文本
            parts = []
            for lang_content in content_obj.values():
                if isinstance(lang_content, dict):
                    for line in lang_content.get("content", []):
                        for elem in line:
                            if elem.get("tag") == "text":
                                parts.append(elem.get("text", ""))
                            elif elem.get("tag") == "a":
                                parts.append(elem.get("href", ""))
            content_text = " ".join(parts) if parts else "[富文本消息]"
        elif msg_type == "image":
            content_text = "[图片消息]"
        elif msg_type == "file":
            content_text = "[文件消息]"
        elif msg_type == "audio":
            content_text = "[语音消息]"
        elif msg_type == "media":
            content_text = "[视频消息]"
        elif msg_type == "sticker":
            content_text = "[表情包]"
        elif msg_type == "interactive":
            content_text = "[卡片消息]"
        elif msg_type == "system":
            content_text = "[系统消息]"
        elif msg_type == "merge_forward":
            # 尝试从展开的详情中获取内容
            expanded = msg.get("_expanded", {})
            items = expanded.get("items", [])
            if items:
                parts = []
                for item in items:
                    item_type = item.get("msg_type", "")
                    item_body = item.get("body", {})
                    item_content = item_body.get("content", "")
                    sender = item.get("sender", {})
                    sender_name = sender.get("id", "未知")
                    # 解析内容
                    try:
                        obj = json.loads(item_content)
                        if item_type == "text":
                            text = obj.get("text", "")
                        elif item_type == "post":
                            text_parts = []
                            for lang_content in obj.values():
                                if isinstance(lang_content, dict):
                                    for line in lang_content.get("content", []):
                                        for elem in line:
                                            if elem.get("tag") == "text":
                                                text_parts.append(elem.get("text", ""))
                            text = " ".join(text_parts) if text_parts else "[富文本]"
                        elif item_type == "image":
                            text = "[图片]"
                        else:
                            text = item_content[:100]
                    except (json.JSONDecodeError, TypeError):
                        text = item_content[:100] if item_content else f"[{item_type}]"
                    parts.append(f"{sender_name}: {text}")
                content_text = "\n    ".join(parts)
            else:
                content_text = content or "[合并转发消息]"
        else:
            content_text = f"[{msg_type}消息]"
    except (json.JSONDecodeError, TypeError):
        content_text = content or f"[{msg_type}消息]"

    sender_label = f"[{sender_type}]{sender_id}" if sender_type else sender_id
    return f"  [{time_str}] {sender_label}: {content_text}"


def format_chat_info(chat):
    """格式化聊天信息"""
    chat_type = chat.get("chat_type", "unknown")
    type_label = "群聊" if chat_type == "group" else "私聊" if chat_type == "p2p" else chat_type
    name = chat.get("name", "") or "(未命名)"
    chat_id = chat.get("chat_id", "")
    member_count = chat.get("user_count", 0)
    return f"[{type_label}] {name} (ID: {chat_id}, 成员: {member_count})"


# ==================== 目标群配置 ====================

# 只读取以下群的消息，其他群和私聊一律不读取
TARGET_GROUPS = [
    "机器人好友",
]

# 读取最近 N 天的消息
READ_DAYS = 7

# ==================== 主流程 ====================

def export_to_file(all_data, filename=None):
    """
    将所有聊天数据导出为 JSON 文件 + 清洗后的 Excel 表格
    :param all_data: dict, 格式为 {chat_info: {chat_id, messages, ...}, ...}
    :param filename: 输出文件名（不含扩展名），默认自动生成带时间戳的文件名
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"feishu_chats_{timestamp}"
    else:
        base = filename.rsplit(".", 1)[0] if "." in filename else filename

    # 1. 导出原始 JSON
    json_path = f"{base}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n原始 JSON 已导出到: {json_path}")

    # 2. 导出清洗后的 Markdown 表格
    md_path = f"{base}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 飞书聊天记录\n\n")
        f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"读取范围: 最近 {READ_DAYS} 天  \n")
        f.write(f"目标群: {', '.join(TARGET_GROUPS)}\n\n")
        f.write("---\n\n")

        for chat_label, chat_data in all_data.items():
            f.write(f"## {chat_label}\n\n")
            f.write("| 序号 | 时间 | 类型 | 发送者 | 内容 |\n")
            f.write("|------|------|------|--------|------|\n")

            messages = chat_data.get("messages", [])
            for idx, msg in enumerate(messages, 1):
                # 时间
                create_time = msg.get("create_time", "")
                if create_time:
                    try:
                        dt = datetime.fromtimestamp(int(create_time) / 1000)
                        time_str = dt.strftime("%m-%d %H:%M")
                    except (ValueError, OSError):
                        time_str = create_time
                else:
                    time_str = ""

                msg_type = msg.get("msg_type", "unknown")
                sender = msg.get("sender", {})
                sender_id = sender.get("id", "") or ""
                content = _extract_clean_content(msg)
                # Markdown 表格中换行用 <br>
                content = content.replace("\n", "<br>")

                f.write(f"| {idx} | {time_str} | {msg_type} | {sender_id} | {content} |\n")

                # 合并转发的子消息
                expanded = msg.get("_expanded", {})
                sub_items = expanded.get("items", [])
                if sub_items:
                    for sub in sub_items:
                        sub_time = sub.get("create_time", "")
                        if sub_time:
                            try:
                                sub_dt = datetime.fromtimestamp(int(sub_time) / 1000)
                                sub_time_str = sub_dt.strftime("%m-%d %H:%M")
                            except (ValueError, OSError):
                                sub_time_str = sub_time
                        else:
                            sub_time_str = ""
                        sub_type = sub.get("msg_type", "")
                        sub_sender = sub.get("sender", {}).get("id", "")
                        sub_content = _extract_clean_content(sub).replace("\n", "<br>")
                        f.write(f"| &nbsp; | {sub_time_str} | {sub_type} | {sub_sender} | {sub_content} |\n")

            f.write("\n")

    print(f"清洗后 Markdown 已导出到: {md_path}")

    return json_path


def _extract_clean_content(msg):
    """从消息中提取清洗后的纯文本内容"""
    msg_type = msg.get("msg_type", "unknown")
    body = msg.get("body", {})
    content = body.get("content", "")

    if msg_type == "system":
        try:
            obj = json.loads(content)
            template = obj.get("template", "")
            from_users = obj.get("from_user", [])
            to_chatters = obj.get("to_chatters", [])
            result = template
            if from_users:
                result = result.replace("{from_user}", ", ".join(from_users))
            if to_chatters:
                result = result.replace("{to_chatters}", ", ".join(to_chatters))
            result = result.replace("{group_type}", "群聊")
            return result
        except (json.JSONDecodeError, TypeError):
            return content

    elif msg_type == "text":
        try:
            return json.loads(content).get("text", content)
        except (json.JSONDecodeError, TypeError):
            return content

    elif msg_type == "post":
        try:
            obj = json.loads(content)
            parts = []
            for lang_content in obj.values():
                if isinstance(lang_content, dict):
                    for line in lang_content.get("content", []):
                        for elem in line:
                            tag = elem.get("tag", "")
                            if tag == "text":
                                parts.append(elem.get("text", ""))
                            elif tag == "a":
                                parts.append(elem.get("href", ""))
                            elif tag == "img":
                                parts.append("[图片]")
            return " ".join(parts) if parts else "[富文本消息]"
        except (json.JSONDecodeError, TypeError):
            return content

    elif msg_type == "image":
        return "[图片]"
    elif msg_type == "file":
        return "[文件]"
    elif msg_type == "audio":
        return "[语音]"
    elif msg_type == "media":
        return "[视频]"
    elif msg_type == "sticker":
        return "[表情包]"
    elif msg_type == "interactive":
        return "[卡片消息]"
    elif msg_type == "merge_forward":
        return "[合并转发消息]（见下方子消息）"
    else:
        return content or f"[{msg_type}消息]"


def main():
    """主流程：只读取 TARGET_GROUPS 中指定的群消息"""
    # 1. 获取 user_access_token
    try:
        token = get_user_access_token()
    except Exception as e:
        print(f"授权失败: {e}")
        return

    # 2. 初始化读取器
    reader = FeishuChatReader(token)

    # 3. 获取当前用户信息
    user_info = reader.get_user_info()
    if user_info:
        print(f"\n当前用户: {user_info.get('name', '未知')} ({user_info.get('user_id', '')})")

    # 4. 获取所有群聊，按名称匹配目标群
    print(f"\n正在获取群聊列表，目标群: {TARGET_GROUPS}")
    group_chats = reader.list_group_chats()
    print(f"  共获取 {len(group_chats)} 个群聊")

    # 按名称精确匹配目标群
    target_chats = []
    for group in group_chats:
        name = group.get("name", "")
        if name in TARGET_GROUPS:
            target_chats.append(group)

    # 检查是否有未匹配的群
    matched_names = {c.get("name") for c in target_chats}
    unmatched = [n for n in TARGET_GROUPS if n not in matched_names]
    if unmatched:
        print(f"\n[警告] 以下群未找到，请检查群名是否正确或你是否在该群中:")
        for n in unmatched:
            print(f"  - {n}")

    if not target_chats:
        print("\n没有找到任何目标群，程序退出。")
        return

    print(f"\n找到 {len(target_chats)}/{len(TARGET_GROUPS)} 个目标群:")
    for i, chat in enumerate(target_chats, 1):
        print(f"  {i}. {format_chat_info(chat)}")

    # 5. 只读取目标群的消息
    print(f"\n正在读取消息记录（最近 {READ_DAYS} 天）...")
    all_data = {}

    for chat in target_chats:
        chat_id = chat.get("chat_id", "")
        chat_label = format_chat_info(chat)

        print(f"\n  读取: {chat_label}")
        messages = reader.get_recent_messages(chat_id, days=READ_DAYS)

        if messages:
            print(f"    获取到 {len(messages)} 条消息")
            all_data[chat_label] = {
                "chat_id": chat_id,
                "chat_type": chat.get("chat_type"),
                "messages": messages,
            }
            # 打印前3条消息预览
            for msg in messages[:3]:
                print(format_message(msg))
            if len(messages) > 3:
                print(f"    ... 还有 {len(messages) - 3} 条消息")
        else:
            print("    无消息")
            all_data[chat_label] = {
                "chat_id": chat_id,
                "chat_type": chat.get("chat_type"),
                "messages": [],
            }

        # 避免触发频率限制
        time.sleep(0.3)

    # 6. 导出结果
    total_msgs = sum(len(v["messages"]) for v in all_data.values())
    print(f"\n{'=' * 60}")
    print(f"读取完成！共 {len(target_chats)} 个群，{total_msgs} 条消息")

    if all_data:
        export_to_file(all_data)

    return all_data


if __name__ == "__main__":
    main()
