"""
群任务存储管理
- JSON 文件持久化
- 支持完成/未完成状态
- 自动去重（同一消息不重复提取）
"""

import json
import os
from datetime import datetime


class TaskStore:
    """群消息提取的任务存储"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"tasks": [], "processed_messages": []}

    def _save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ---------- 消息去重 ----------

    def is_message_processed(self, message_id):
        return message_id in self.data.get("processed_messages", [])

    def mark_message_processed(self, message_id):
        msgs = self.data.setdefault("processed_messages", [])
        if message_id not in msgs:
            msgs.append(message_id)
            # 只保留最近 5000 条
            if len(msgs) > 5000:
                self.data["processed_messages"] = msgs[-5000:]
            self._save()

    # ---------- 任务 CRUD ----------

    def add_task(self, task_dict):
        task = {
            "id": f"grp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.data['tasks'])}",
            "content": task_dict.get("content", ""),
            "sender": task_dict.get("sender", ""),
            "source_message_id": task_dict.get("source_message_id", ""),
            "source_group": task_dict.get("source_group", ""),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "completed": False,
            "completed_at": None,
        }
        self.data["tasks"].append(task)
        self._save()
        return task

    def add_tasks(self, task_list):
        added = []
        for t in task_list:
            added.append(self.add_task(t))
        return added

    def mark_completed(self, task_id):
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                task["completed"] = True
                task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save()
                return True
        return False

    def mark_uncompleted(self, task_id):
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                task["completed"] = False
                task["completed_at"] = None
                self._save()
                return True
        return False

    def get_uncompleted(self):
        return [t for t in self.data["tasks"] if not t.get("completed")]

    def get_all(self):
        return self.data["tasks"]

    def get_by_id(self, task_id):
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                return task
        return None
