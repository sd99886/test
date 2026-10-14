"""
群任务管理 CLI
用法:
    python task_cli.py list              # 列出未完成任务
    python task_cli.py list --all        # 列出所有任务
    python task_cli.py done <id>         # 标记任务完成
    python task_cli.py undo <id>         # 取消完成
    python task_cli.py check             # 检查群消息中的新 @mention
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    APP_ID, APP_SECRET, TARGET_GROUP_NAME, MENTION_NAMES, TARGET_OPEN_ID,
    AI_API_KEY, AI_BASE_URL, AI_MODEL,
    NOTIFY_USER_OPEN_ID,
)
from task_store import TaskStore
from monitor import GroupMonitor
from extractor import TaskExtractor
from notifier import Notifier

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(SCRIPT_DIR, "group_tasks.json")


def cmd_list(args):
    store = TaskStore(TASKS_FILE)
    tasks = store.get_all() if args.all else store.get_uncompleted()
    if not tasks:
        print("暂无任务。")
        return
    label = "所有任务" if args.all else "未完成任务"
    print(f"\n{label}（共 {len(tasks)} 条）:\n")
    for i, t in enumerate(tasks, 1):
        status = "[x]" if t.get("completed") else "[ ]"
        print(f"  {i}. [{t['id']}] {status} {t['content']}")
        print(f"     来自: {t.get('sender', '未知')} | {t.get('created_at', '')}")


def cmd_done(args):
    store = TaskStore(TASKS_FILE)
    tasks = store.get_all()
    if args.index < 1 or args.index > len(tasks):
        print(f"无效序号: {args.index}（有效范围: 1-{len(tasks)}）")
        return
    task = tasks[args.index - 1]
    store.mark_completed(task["id"])
    print(f"[x] 已标记完成: [{task['id']}] {task['content']}")


def cmd_undo(args):
    store = TaskStore(TASKS_FILE)
    tasks = store.get_all()
    if args.index < 1 or args.index > len(tasks):
        print(f"无效序号: {args.index}（有效范围: 1-{len(tasks)}）")
        return
    task = tasks[args.index - 1]
    store.mark_uncompleted(task["id"])
    print(f"[ ] 已取消完成: [{task['id']}] {task['content']}")


def cmd_check(args):
    """检查群消息中的新 @mention 并提取任务"""
    print("检查群消息中的 @mention...\n")
    monitor = GroupMonitor(APP_ID, APP_SECRET, TARGET_GROUP_NAME, MENTION_NAMES,
                           target_open_id=TARGET_OPEN_ID)
    extractor = TaskExtractor(AI_API_KEY, AI_BASE_URL, AI_MODEL)
    store = TaskStore(TASKS_FILE)
    notifier = Notifier(APP_ID, APP_SECRET, user_open_id=NOTIFY_USER_OPEN_ID)

    mentions, _ = monitor.check_new_mentions()

    if not mentions:
        print("没有新的 @mention 消息。")
        return

    print(f"发现 {len(mentions)} 条 @mention 消息:\n")
    all_new_tasks = []

    for msg in mentions:
        msg_id = msg.get("message_id", "")
        if store.is_message_processed(msg_id):
            print(f"  [跳过] 已处理: {msg_id}")
            continue

        text = monitor.get_message_text(msg)
        sender = monitor.get_sender_name(msg)
        print(f"  来自 {sender}: {text[:80]}...")

        # 先判断是否是工作任务（过滤闲聊）
        if not extractor.is_work_task(text):
            store.mark_message_processed(msg_id)
            print(f"  → [过滤] 非工作任务，跳过")
            continue

        tasks = extractor.extract(text, sender)
        if tasks:
            for t in tasks:
                t["source_message_id"] = msg_id
                t["sender"] = sender
                t["source_group"] = TARGET_GROUP_NAME
            added = store.add_tasks(tasks)
            all_new_tasks.extend(added)
            store.mark_message_processed(msg_id)
            print(f"  → 提取 {len(added)} 条任务")
            for t in added:
                print(f"    - {t['content']}")
                notifier.send_task_notification(t["content"], sender)
        else:
            store.mark_message_processed(msg_id)
            print(f"  → 未提取到任务")
        print()

    if all_new_tasks:
        print(f"共新增 {len(all_new_tasks)} 条任务，已发送通知。")
    else:
        print("未提取到新任务。")


def main():
    parser = argparse.ArgumentParser(description="群任务管理")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="列出任务")
    p_list.add_argument("--all", action="store_true", help="显示所有任务（含已完成）")

    p_done = sub.add_parser("done", help="标记任务完成")
    p_done.add_argument("index", type=int, help="任务序号")

    p_undo = sub.add_parser("undo", help="取消完成")
    p_undo.add_argument("index", type=int, help="任务序号")

    sub.add_parser("check", help="检查群消息中的新 @mention")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"list": cmd_list, "done": cmd_done, "undo": cmd_undo, "check": cmd_check}[args.command](args)


if __name__ == "__main__":
    main()
