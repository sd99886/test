"""
飞书通知推送
- 方式 1：通过飞书应用机器人发送私聊消息
- 方式 2：通过群 Webhook 机器人发送消息
"""

import json
import requests


class Notifier:
    """飞书通知推送"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id="", app_secret="", webhook_url="", user_open_id="", group_chat_id=""):
        self.app_id = app_id
        self.app_secret = app_secret
        self.webhook_url = webhook_url
        self.user_open_id = user_open_id
        self.group_chat_id = group_chat_id

    def _get_tenant_token(self):
        """获取 tenant_access_token（用于机器人发消息）"""
        resp = requests.post(f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret})
        data = resp.json()
        return data.get("tenant_access_token", "")

    def send_text(self, text):
        """发送文本通知（优先私聊给用户，其次 webhook）"""
        if self.user_open_id and self.app_id:
            return self._send_bot_message(text)
        if self.webhook_url:
            return self._send_webhook(text)
        return False

    def _send_to_group(self, text):
        """通过机器人发送消息到群"""
        token = self._get_tenant_token()
        if not token:
            print("  [通知] 获取 tenant_token 失败")
            return False

        resp = requests.post(
            f"{self.BASE_URL}/im/v1/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params={"receive_id_type": "chat_id"},
            json={
                "receive_id": self.group_chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }
        )
        data = resp.json()
        if data.get("code") != 0:
            print(f"  [通知] 群消息发送失败: {data.get('msg', '')}")
            return False
        return True

    def _send_bot_message(self, text):
        """通过应用机器人发送私聊消息"""
        token = self._get_tenant_token()
        if not token:
            print("  [通知] 获取 tenant_token 失败")
            return False

        resp = requests.post(
            f"{self.BASE_URL}/im/v1/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params={"receive_id_type": "open_id"},
            json={
                "receive_id": self.user_open_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }
        )
        data = resp.json()
        if data.get("code") != 0:
            print(f"  [通知] 发送失败: {data.get('msg', '')}")
            return False
        return True

    def _send_webhook(self, text):
        """通过 Webhook 发送消息"""
        resp = requests.post(self.webhook_url,
            json={"msg_type": "text", "content": {"text": text}})
        data = resp.json()
        if data.get("code") != 0 and data.get("StatusCode") != 0:
            print(f"  [通知] Webhook 发送失败: {data}")
            return False
        return True

    def send_task_notification(self, task_content, sender_name=""):
        """发送新任务通知"""
        prefix = f"📋 新工作任务（来自: {sender_name}）\n" if sender_name else "📋 新工作任务\n"
        text = f"{prefix}{task_content}"
        return self.send_text(text)
