"""翻页查找「机器人好友」群"""
import sys
sys.path.insert(0, r"c:\Users\Cupshe\Desktop\test\feishu_api")

from feishu_chat_reader import get_user_access_token
import requests, json

token = get_user_access_token()
headers = {"Authorization": f"Bearer {token}"}
url = "https://open.feishu.cn/open-apis/im/v1/chats"

all_groups = []
page_token = None

while True:
    params = {"page_size": 50, "chat_type": "group"}
    if page_token:
        params["page_token"] = page_token

    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    if data.get("code") != 0:
        print(f"错误: {data}")
        break

    items = data["data"].get("items", [])
    all_groups.extend(items)

    if not data["data"].get("has_more"):
        break
    page_token = data["data"].get("page_token")

print(f"\n共获取 {len(all_groups)} 个群\n")

# 搜索目标群
target = "机器人好友"
for i, chat in enumerate(all_groups, 1):
    name = chat.get("name", "")
    if target in name or name in target:
        print(f"  >>> 匹配! [{name}] chat_id={chat.get('chat_id')}")
    # 也打印包含"机器人"或"好友"的
    if "机器人" in name or "好友" in name or "Feishu" in name or "Assistant" in name:
        print(f"  >>> 疑似: [{name}] chat_id={chat.get('chat_id')}")

# 列出所有群名方便用户确认
print(f"\n=== 所有 {len(all_groups)} 个群名 ===")
for i, chat in enumerate(all_groups, 1):
    print(f"  {i}. {chat.get('name', '(未命名)')}")
