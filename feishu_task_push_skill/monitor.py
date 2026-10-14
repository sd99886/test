"""
飞书群消息监听器
- 轮询目标群的新消息
- 检测 @mention 消息
- 提取消息文本内容
"""

import json
import os
import time
import webbrowser
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime


class GroupMonitor:
    """飞书群消息监听器"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id, app_secret, target_group_name, mention_names,
                 target_open_id="",
                 redirect_uri="http://localhost:8899/callback",
                 scope="im:chat im:message im:message:readonly"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.target_group_name = target_group_name
        self.mention_names = mention_names
        self.target_open_id = target_open_id
        self.redirect_uri = redirect_uri
        self.scope = scope
        self._token = None
        self._token_expires_at = 0
        self._chat_id = None
        self._last_check_time = None

    # ==================== OAuth2 ====================

    def get_token(self):
        """获取 user_access_token（优先使用已有缓存）"""
        if self._token and time.time() < self._token_expires_at - 300:
            return self._token

        # 尝试读取 monitor 自己的缓存
        cache_file = os.path.join(os.path.dirname(__file__), ".monitor_token_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                token = cache.get("access_token", "")
                expires_at = cache.get("expires_at", 0)
                if token and time.time() < expires_at - 300:
                    self._token = token
                    self._token_expires_at = expires_at
                    return token
            except Exception:
                pass

        # 尝试复用 feishu_project_push 的 task token 缓存
        task_cache = os.path.join(os.path.dirname(__file__), ".user_task_token_cache.json")
        if os.path.exists(task_cache):
            try:
                with open(task_cache, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                token = cache.get("access_token", "") or cache.get("token", "")
                expires_at = cache.get("expires_at", 0)
                if expires_at < 1e12:
                    expires_at = time.time() + expires_at
                if token and time.time() < expires_at - 300:
                    self._token = token
                    self._token_expires_at = expires_at
                    return token
            except Exception:
                pass

        return self._do_oauth()

    def _do_oauth(self):
        auth_url = (
            f"{self.BASE_URL}/authen/v1/authorize"
            f"?app_id={self.app_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state=monitor"
            f"&scope={self.scope}"
        )
        print(f"\n  群监听需要授权，请在浏览器中完成授权:")
        print(f"  {auth_url}\n")
        webbrowser.open(auth_url)

        class Handler(BaseHTTPRequestHandler):
            auth_code = None
            def do_GET(self):
                query = parse_qs(urlparse(self.path).query)
                if "code" in query:
                    Handler.auth_code = query["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write("授权成功！请回到终端查看结果。".encode("utf-8"))
                else:
                    self.send_response(400)
                    self.end_headers()
            def log_message(self, format, *args): pass

        server = HTTPServer(("localhost", 8899), Handler)
        server.timeout = 120
        Handler.auth_code = None
        threading.Thread(target=server.handle_request).start()
        time.sleep(0.5)

        # 等待回调或超时
        for _ in range(240):
            if Handler.auth_code:
                break
            time.sleep(0.5)
        server.server_close()

        code = Handler.auth_code
        if not code:
            raise Exception("授权超时或失败。请手动授权后提供 code。")

        # 用 code 换取 token
        r1 = requests.post(f"{self.BASE_URL}/auth/v3/app_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret})
        app_token = r1.json().get("app_access_token", "")

        r2 = requests.post(f"{self.BASE_URL}/authen/v1/oidc/access_token",
            headers={"Authorization": f"Bearer {app_token}"},
            json={"grant_type": "authorization_code", "code": code})
        data = r2.json()
        if data.get("code") != 0:
            raise Exception(f"获取 token 失败: {data}")

        token_data = data["data"]
        self._token = token_data["access_token"]
        self._token_expires_at = time.time() + token_data.get("expires_in", 7200)

        # 缓存
        cache_file = os.path.join(os.path.dirname(__file__), ".monitor_token_cache.json")
        with open(cache_file, "w") as f:
            json.dump({"access_token": self._token, "expires_at": self._token_expires_at}, f)

        return self._token

    # ==================== 群消息 ====================

    def _headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}

    def find_target_group(self):
        """查找目标群的 chat_id"""
        if self._chat_id:
            return self._chat_id

        chats = []
        page_token = None
        while True:
            params = {"page_size": 50, "chat_type": "group"}
            if page_token:
                params["page_token"] = page_token
            r = requests.get(f"{self.BASE_URL}/im/v1/chats",
                headers=self._headers(), params=params)
            data = r.json()
            if data.get("code") != 0:
                print(f"  [错误] 获取群列表失败: {data.get('msg', '')}")
                return None
            items = data.get("data", {}).get("items", [])
            chats.extend(items)
            if not data.get("data", {}).get("has_more"):
                break
            page_token = data.get("data", {}).get("page_token")

        for chat in chats:
            if chat.get("name") == self.target_group_name:
                self._chat_id = chat.get("chat_id")
                print(f"  [监听] 找到目标群: {self.target_group_name} ({self._chat_id})")
                return self._chat_id

        print(f"  [错误] 未找到群: {self.target_group_name}")
        print(f"  可用群列表:")
        for c in chats[:20]:
            print(f"    - {c.get('name', '(未命名)')}")
        return None

    def get_new_messages(self, chat_id, start_time=None):
        """获取新消息（按时间升序）"""
        messages = []
        page_token = None
        while True:
            params = {
                "container_id_type": "chat",
                "container_id": chat_id,
                "page_size": 50,
                "sort_type": "ByCreateTimeAsc",
            }
            if start_time:
                params["start_time"] = start_time
            if page_token:
                params["page_token"] = page_token

            r = requests.get(f"{self.BASE_URL}/im/v1/messages",
                headers=self._headers(), params=params)
            data = r.json()
            if data.get("code") != 0:
                print(f"  [错误] 获取消息失败: {data.get('msg', '')}")
                break

            items = data.get("data", {}).get("items", [])
            messages.extend(items)
            if not data.get("data", {}).get("has_more"):
                break
            page_token = data.get("data", {}).get("page_token")

        return messages

    # ==================== @mention 检测 ====================

    def is_at_me(self, message):
        """检测消息是否 @了目标用户"""
        msg_type = message.get("msg_type", "")

        # 跳过系统消息（入群/退群等）
        if msg_type == "system":
            return False

        # 1. 检查消息顶层的 mentions 数组（优先用 open_id 匹配，不受改名影响）
        mentions = message.get("mentions", [])
        for mention in mentions:
            mention_id = mention.get("id", "")
            mention_name = mention.get("name", "")
            # 优先用 open_id 精确匹配
            if self.target_open_id and mention_id == self.target_open_id:
                return True
            # 备用：名字匹配
            for name in self.mention_names:
                if name == mention_name or name in mention_name or name in mention_id:
                    return True

        # 2. 富文本消息中的 at 元素（额外检查）
        if msg_type == "post":
            body = message.get("body", {})
            content_str = body.get("content", "")
            try:
                obj = json.loads(content_str)
                for lang_content in obj.values():
                    if isinstance(lang_content, dict):
                        for line in lang_content.get("content", []):
                            for elem in line:
                                if elem.get("tag") == "at":
                                    user_id = elem.get("user_id", "")
                                    user_name = elem.get("user_name", "")
                                    for name in self.mention_names:
                                        if name == user_name or name in user_name or name in user_id:
                                            return True
            except (json.JSONDecodeError, TypeError):
                pass

        # 3. 文本回退匹配（检查消息内容中的名字）
        text = self.get_message_text(message)
        for name in self.mention_names:
            if name in text:
                return True

        return False

    def get_message_text(self, message):
        """提取消息纯文本（将 @_user_1 占位符替换为实际名字）"""
        msg_type = message.get("msg_type", "")
        body = message.get("body", {})
        content_str = body.get("content", "")

        # 构建 mentions 映射：@_user_1 -> 名字
        mention_map = {}
        for m in message.get("mentions", []):
            key = m.get("key", "")
            name = m.get("name", "")
            if key:
                mention_map[key] = name

        if msg_type == "text":
            try:
                text = json.loads(content_str).get("text", "")
            except (json.JSONDecodeError, TypeError):
                text = content_str
            # 替换 @_user_1 占位符
            for placeholder, name in mention_map.items():
                text = text.replace(placeholder, f"@{name}")
            return text
        elif msg_type == "post":
            try:
                obj = json.loads(content_str)
                parts = []
                for lang_content in obj.values():
                    if isinstance(lang_content, dict):
                        for line in lang_content.get("content", []):
                            for elem in line:
                                if elem.get("tag") == "text":
                                    parts.append(elem.get("text", ""))
                                elif elem.get("tag") == "at":
                                    parts.append(f"@{elem.get('user_name', '')}")
                return " ".join(parts)
            except (json.JSONDecodeError, TypeError):
                return content_str
        elif msg_type in ("image", "file", "audio", "media", "sticker"):
            return f"[{msg_type}]"
        else:
            return content_str or f"[{msg_type}]"

    def get_sender_name(self, message):
        """获取发送者名称"""
        sender = message.get("sender", {})
        return sender.get("id", "未知")

    # ==================== 轮询 ====================

    def check_new_mentions(self):
        """检查新的 @mention 消息，返回 (mention_messages, new_check_time)"""
        chat_id = self.find_target_group()
        if not chat_id:
            return [], None

        start_time = self._last_check_time
        if not start_time:
            # 首次运行，检查最近 1 天
            start_time = str(int(time.time()) - 86400)

        messages = self.get_new_messages(chat_id, start_time=start_time)

        mentions = []
        for msg in messages:
            if self.is_at_me(msg):
                mentions.append(msg)

        # 更新检查时间（秒级时间戳）
        new_check_time = str(int(time.time()))
        self._last_check_time = new_check_time

        return mentions, new_check_time

    def set_check_time(self, timestamp_sec):
        """手动设置上次检查时间（秒级时间戳）"""
        self._last_check_time = timestamp_sec
