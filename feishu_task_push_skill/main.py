"""
飞书项目每日任务推送（MCP Server + 飞书任务 + 群消息任务）

数据源：
1. 飞书项目 MCP Server - Epic 视图中的工作项
2. 飞书「任务」模块 - 个人任务列表
3. 群消息任务 - 从指定群 @mention 中提取的工作任务

用法:
    python main.py              # 正常查询并输出
"""

import json
import os
import sys
import time
import webbrowser
import threading
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    MCP_TOKEN, MCP_SERVER_URL, VIEW_ID, PROJECT_KEY,
    TARGET_PERSON_NAME, TARGET_USER_KEY,
    APP_ID, APP_SECRET,
    OUTPUT_DIR,
    TARGET_GROUP_NAME, MENTION_NAMES,
    AI_API_KEY, AI_BASE_URL, AI_MODEL,
    NOTIFY_USER_OPEN_ID,
)
from task_store import TaskStore
from monitor import GroupMonitor
from extractor import TaskExtractor
from notifier import Notifier

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 工作项类型映射
TYPE_LABELS = {
    "story": "Story", "issue": "缺陷", "sub_task": "任务",
    "chart": "图表", "epic": "Epic",
    "655aecf3e1f41a486de6bed7": "Epic",
}

# 工作项类型到 URL 路径的映射（URL 中使用英文小写）
TYPE_URL_MAP = {
    "Story": "story", "缺陷": "issue", "任务": "sub_task",
    "图表": "chart", "Epic": "epic",
}

# 飞书项目任务链接模板
# https://project.feishu.cn/{simple_name}/{type_name_lowercase}/detail/{work_item_id}
PROJECT_LINK_TEMPLATE = "https://project.feishu.cn/cupshe_rdc/{type_name_lower}/detail/{item_id}"

# 飞书任务链接模板
# https://feishu.cn/task/{task_guid}
TASK_LINK_TEMPLATE = "https://feishu.cn/task/{task_guid}"


# ==================== MCP 客户端（飞书项目） ====================

class McpClient:
    """飞书项目 MCP Server 客户端"""

    def __init__(self, token, server_url):
        self.token = token
        self.server_url = server_url
        self._headers = {"Content-Type": "application/json", "X-Mcp-Token": token}

    def call(self, tool_name, arguments):
        resp = requests.post(self.server_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": tool_name, "arguments": arguments}},
            headers=self._headers)
        data = resp.json()
        if data.get("result", {}).get("isError"):
            content = data["result"].get("content", [{}])
            err_text = content[0].get("text", "") if content else "未知错误"
            raise Exception(f"MCP {tool_name} 失败: {err_text}")
        return data

    def get_view_detail(self, project_key, view_id):
        """获取视图下的所有工作项（自动分页）"""
        all_items = []
        page_num = 1
        while True:
            result = self.call("get_view_detail", {
                "project_key": project_key,
                "view_id": view_id,
                "page_num": page_num,
                "page_size": 50,
            })
            text = result["result"]["content"][0]["text"]
            data = json.loads(text)
            items = data.get("work_item_list", [])
            all_items.extend(items)
            pagination = data.get("pagination", {})
            total = pagination.get("total", 0)
            has_more = pagination.get("has_more", False)
            print(f"  [项目] 第 {page_num} 页: {len(items)} 条 (总计 {total})")
            if not has_more or not items:
                break
            page_num += 1
        return all_items


# ==================== 飞书任务客户端 ====================

class FeishuTaskClient:
    """飞书「任务」模块 API 客户端（使用 OAuth2 user_access_token）"""

    BASE_URL = "https://open.feishu.cn/open-apis"
    REDIRECT_URI = "http://localhost:8899/callback"
    LOCAL_PORT = 8899
    TOKEN_CACHE_FILE = os.path.join(SCRIPT_DIR, ".user_task_token_cache.json")

    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret

    def _get_app_token(self):
        """获取 app_access_token"""
        resp = requests.post(f"{self.BASE_URL}/auth/v3/app_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret})
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取 app_access_token 失败: {data}")
        return data["app_access_token"]

    def _do_oauth(self):
        """执行 OAuth2 授权流程获取 user_access_token"""
        auth_url = (
            f"{self.BASE_URL}/authen/v1/authorize"
            f"?app_id={self.app_id}"
            f"&redirect_uri={self.REDIRECT_URI}"
            f"&state=task_reader"
            f"&scope=task:task:read"
        )
        print("\n  需要授权以读取飞书「任务」")
        print(f"  请在浏览器中完成授权: {auth_url}\n")
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

        server = HTTPServer(("localhost", self.LOCAL_PORT), Handler)
        server.timeout = 120
        Handler.auth_code = None
        threading.Thread(target=server.handle_request).start()
        time.sleep(0.5)
        server.server_close()

        code = Handler.auth_code
        if not code:
            raise Exception("授权超时或失败")

        # 用 code 换取 user_access_token
        app_token = self._get_app_token()
        resp = requests.post(f"{self.BASE_URL}/authen/v1/oidc/access_token",
            headers={"Authorization": f"Bearer {app_token}"},
            json={"grant_type": "authorization_code", "code": code})
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取 user_access_token 失败: {data}")

        token_data = data["data"]
        token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 7200)
        user_name = token_data.get("name", "")
        print(f"  授权成功！用户: {user_name}")

        # 缓存
        with open(self.TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"token": token, "expires_at": time.time() + expires_in,
                        "user_name": user_name}, f)
        return token

    def _refresh_token(self, refresh_token):
        """使用 refresh_token 刷新 user_access_token"""
        app_token = self._get_app_token()
        resp = requests.post(f"{self.BASE_URL}/authen/v1/oidc/refresh_access_token",
            headers={"Authorization": f"Bearer {app_token}"},
            json={"grant_type": "refresh_token", "refresh_token": refresh_token})
        data = resp.json()
        if data.get("code") != 0:
            return None
        token_data = data["data"]
        token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 7200)
        new_refresh = token_data.get("refresh_token", refresh_token)
        # 更新缓存
        with open(self.TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        cache["token"] = token
        cache["access_token"] = token
        cache["expires_at"] = time.time() + expires_in
        cache["refresh_token"] = new_refresh
        with open(self.TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        return token

    def get_user_token(self):
        """获取 user_access_token（带缓存，支持 refresh_token 刷新）"""
        if os.path.exists(self.TOKEN_CACHE_FILE):
            try:
                with open(self.TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                # 兼容两种缓存格式
                token = cache.get("token") or cache.get("access_token", "")
                expires_at = cache.get("expires_at", 0)
                # expires_at 可能是秒数或时间戳
                if expires_at < 1e12:
                    expires_at = time.time() + expires_at
                if token and time.time() < expires_at - 300:
                    return token
                # Token 过期，尝试用 refresh_token 刷新
                refresh_token = cache.get("refresh_token")
                if refresh_token:
                    new_token = self._refresh_token(refresh_token)
                    if new_token:
                        print("  [OK] Token 已自动刷新")
                        return new_token
            except Exception:
                pass
        return self._do_oauth()

    def list_tasks(self, page_size=50):
        """获取当前用户的任务列表"""
        token = self.get_user_token()
        headers = {"Authorization": f"Bearer {token}"}
        all_tasks = []
        page_token = None

        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(f"{self.BASE_URL}/task/v2/tasks",
                headers=headers, params=params)
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(f"获取任务失败: {data.get('msg', data)}")
            tasks = data.get("data", {}).get("items", [])
            all_tasks.extend(tasks)
            has_more = data.get("data", {}).get("has_more", False)
            page_token = data.get("data", {}).get("page_token")
            print(f"  [任务] 获取 {len(tasks)} 条 (累计 {len(all_tasks)})")
            if not has_more or not tasks:
                break
        return all_tasks


# ==================== 业务逻辑 ====================

class TaskPush:
    """每日任务推送"""

    def __init__(self):
        self.mcp = McpClient(MCP_TOKEN, MCP_SERVER_URL)
        self.task_client = FeishuTaskClient(APP_ID, APP_SECRET)
        self.target_name = TARGET_PERSON_NAME
        self.target_user_key = TARGET_USER_KEY
        self.group_tasks_file = os.path.join(SCRIPT_DIR, "group_tasks.json")
        self.group_store = TaskStore(self.group_tasks_file)

    # ----- 飞书项目任务 -----

    def query_project_tasks(self):
        """从 MCP Server 获取飞书项目任务"""
        print("[1/2] 查询飞书项目任务...")
        all_items = self.mcp.get_view_detail(PROJECT_KEY, VIEW_ID)
        print(f"  视图共 {len(all_items)} 条工作项")

        filtered = [item for item in all_items if self._is_target_owner(item)]
        print(f"  {self.target_name} 负责: {len(filtered)} 条\n")
        return filtered

    def _is_target_owner(self, item):
        for field in item.get("work_item_fields", []):
            if field.get("key") == "current_status_operator":
                for v in field.get("value", []):
                    if v.get("key") == self.target_user_key:
                        return True
        for node in item.get("work_item_current_node", []):
            for owner in node.get("owners", []):
                if owner.get("key") == self.target_user_key:
                    return True
        return False

    def parse_project_item(self, item):
        """解析飞书项目工作项"""
        attr = item.get("work_item_attribute", {})
        nodes = item.get("work_item_current_node", [])
        fields = item.get("work_item_fields", [])

        item_id = attr.get("work_item_id", "")
        name = attr.get("work_item_name", "")
        type_info = attr.get("work_item_type", {})
        type_key = type_info.get("key", "")
        type_name = TYPE_LABELS.get(type_key, type_info.get("name", type_key))
        status_name = attr.get("work_item_status", {}).get("name", "-")
        node_name = nodes[0].get("name", "-") if nodes else "-"

        # 当前负责人
        owner = "-"
        for field in fields:
            if field.get("key") == "current_status_operator":
                names = [v.get("name", "") for v in field.get("value", []) if v.get("name")]
                owner = ", ".join(names) if names else "-"
                break

        # 更新时间
        update_time = attr.get("update_time", "")
        update_str = update_time[:10] if update_time else "-"

        # 任务链接（使用 type name 映射到 URL 路径）
        type_name_lower = TYPE_URL_MAP.get(type_name, type_name.lower())
        link = PROJECT_LINK_TEMPLATE.format(type_name_lower=type_name_lower, item_id=item_id)

        return {
            "source": "飞书项目",
            "id": str(item_id),
            "name": name,
            "type": type_name,
            "status": status_name,
            "node": node_name,
            "owner": owner,
            "update_time": update_str,
            "link": link,
        }

    # ----- 飞书「任务」模块 -----

    def query_feishu_tasks(self):
        """从飞书任务 API 获取个人任务"""
        print("[2/2] 查询飞书「任务」模块...")
        try:
            tasks = self.task_client.list_tasks()
        except Exception as e:
            print(f"  [错误] {e}")
            return []
        # user_access_token 返回的已经是当前用户的任务
        print(f"  共 {len(tasks)} 条任务\n")
        return tasks

    def parse_feishu_task(self, task):
        """解析飞书任务"""
        task_guid = task.get("guid", "")
        summary = task.get("summary", "")
        if len(summary) > 50:
            summary = summary[:47] + "..."

        # 状态判断：completed_at 为 "0" 或空表示未完成
        completed_at = task.get("completed_at", "0")
        status_label = "已完成" if completed_at and completed_at != "0" else "进行中"

        # 截止时间
        due = task.get("due", {})
        due_str = "-"
        if due:
            ts = due.get("timestamp", "")
            if ts:
                try:
                    due_str = datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    pass

        # 链接（优先使用 API 返回的 url）
        link = task.get("url", "") or TASK_LINK_TEMPLATE.format(task_guid=task_guid)

        # 创建者（API 返回的是 id，暂显示为 id）
        creator = task.get("creator", {})
        creator_name = creator.get("name", creator.get("id", "-")[:8])

        return {
            "source": "飞书任务",
            "id": task_guid[:12] if task_guid else "-",
            "name": summary,
            "type": "任务",
            "status": status_label,
            "node": "-",
            "owner": creator_name,
            "update_time": due_str,
            "link": link,
        }

    # ----- 群消息任务 -----

    def query_group_tasks(self):
        """从群消息中提取的所有任务（含已完成）"""
        print("[3/3] 查询群消息任务...")
        all_tasks = self.group_store.get_all()
        uncompleted = [t for t in all_tasks if not t.get('completed')]
        completed = [t for t in all_tasks if t.get('completed')]
        print(f"  共 {len(all_tasks)} 条任务 (未完成: {len(uncompleted)}, 已完成: {len(completed)})\n")
        return all_tasks

    def parse_group_task(self, task):
        """解析群任务为统一格式"""
        content = task.get("content", "")
        if len(content) > 50:
            content = content[:47] + "..."
        
        # 判断状态和完成时间
        is_completed = task.get("completed", False)
        status_label = "已完成" if is_completed else "进行中"
        completed_time = task.get("completed_at", "")
        
        return {
            "source": "群任务",
            "id": task.get("id", "-"),
            "name": content,
            "type": "任务",
            "status": status_label,
            "node": "-",
            "owner": task.get("sender", "-"),
            "update_time": completed_time[:16] if completed_time else task.get("created_at", "-")[:10],
            "link": "",
            "task_id": task.get("id", ""),
            "completed": is_completed,
            "completed_at": completed_time,
        }

    # ----- 格式化输出 -----

    def format_table(self, project_items, feishu_tasks, group_tasks=None):
        """格式化为 Markdown 表格（分两页：进行中 + 已完成）"""
        all_parsed = []

        for item in project_items:
            all_parsed.append(self.parse_project_item(item))
        for task in feishu_tasks:
            all_parsed.append(self.parse_feishu_task(task))
        if group_tasks:
            for task in group_tasks:
                all_parsed.append(self.parse_group_task(task))

        if not all_parsed:
            return "暂无任务。", [], []

        # 分离进行中和已完成
        in_progress = [p for p in all_parsed if not p.get("completed")]
        completed = [p for p in all_parsed if p.get("completed")]

        # 生成表格函数
        def gen_table(items, title=""):
            if not items:
                return f"### {title}\n\n暂无{title}任务。\n"
            lines = [
                f"### {title}",
                "",
                "| 序号 | 完成 | 来源 | 标题 | 类型 | 状态 | 当前节点 | 负责人 | 截止/更新 | 链接 |",
                "|:----:|:----:|:----:|------|:----:|:----:|:--------:|:------:|:--------:|:----:|",
            ]
            for idx, p in enumerate(items, 1):
                name = p["name"].replace("|", "\\|").replace("\n", " ")
                if len(name) > 35:
                    name = name[:32] + "..."
                link = f"[打开]({p['link']})" if p.get("link") else "-"
                checkbox = "[x]" if p.get("completed") else "[ ]"
                lines.append(
                    f"| {idx} | {checkbox} | {p['source']} | {name} | {p['type']} "
                    f"| {p['status']} | {p['node']} | {p['owner']} "
                    f"| {p['update_time']} | {link} |"
                )
            return "\n".join(lines)

        table_in_progress = gen_table(in_progress, "进行中")
        table_completed = gen_table(completed, "[已完成]")
        full_table = table_in_progress + "\n\n" + table_completed

        return full_table, in_progress, completed

    def export(self, all_parsed, table_text):
        """导出到文件"""
        output_dir = os.path.join(SCRIPT_DIR, OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)

        today = datetime.now().strftime("%Y%m%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Markdown
        md_path = os.path.join(output_dir, f"daily_tasks_{today}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# 每日任务推送\n\n")
            f.write(f"- 日期: {now_str}\n")
            f.write(f"- 负责人: {self.target_name}\n")
            f.write(f"- 任务数: {len(all_parsed)}\n\n")
            f.write(table_text)
            f.write("\n")
        print(f"[导出] Markdown: {md_path}")

        # JSON
        json_path = os.path.join(output_dir, f"daily_tasks_{today}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "date": today,
                "generated_at": now_str,
                "target_person": self.target_name,
                "total": len(all_parsed),
                "tasks": all_parsed,
            }, f, ensure_ascii=False, indent=2)
        print(f"[导出] JSON:     {json_path}")

        return md_path, json_path

    def run(self):
        """执行每日任务推送"""
        print(f"{'=' * 60}")
        print(f"  飞书每日任务推送")
        print(f"  日期: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"  负责人: {self.target_name}")
        print(f"{'=' * 60}\n")

        # 1. 飞书项目任务
        project_items = self.query_project_tasks()

        # 2. 飞书「任务」模块
        feishu_tasks = self.query_feishu_tasks()

        # 3. 群消息任务
        group_tasks = self.query_group_tasks()

        # 4. 合并输出
        table_text, in_progress, completed = self.format_table(project_items, feishu_tasks, group_tasks)

        project_count = len(project_items)
        task_count = len(feishu_tasks)
        group_count = len(group_tasks)
        total_count = len(in_progress) + len(completed)

        print(f"{'=' * 60}")
        print(f"  任务汇总: 飞书项目 {project_count} + 飞书任务 {task_count} + 群任务 {group_count} = 共 {total_count} 条")
        print(f"  进行中: {len(in_progress)} | 已完成: {len(completed)}")
        print(f"{'=' * 60}\n")
        print(table_text)

        if total_count > 0:
            self.export(in_progress + completed, table_text)

        print(f"\n{'=' * 60}")
        print(f"  推送完成!")
        print(f"  管理群任务: python task_cli.py list / done <序号>")
        print(f"{'=' * 60}")


# ==================== 入口 ====================

def main():
    if not MCP_TOKEN:
        print("[错误] 请先在 config.py 中填写 MCP_TOKEN")
        sys.exit(1)
    TaskPush().run()


if __name__ == "__main__":
    main()
