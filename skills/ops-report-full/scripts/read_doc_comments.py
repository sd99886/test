# -*- coding: utf-8 -*-
"""读取文档 YOUR_DOC_ID 的全部评论及回复"""
import json, os, sys, io, time, requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
from publish_report import load_token
TOK = load_token()
OPEN = "https://open.feishu.cn/open-apis"
DOC = "YOUR_DOC_ID"
H = {"Authorization": f"Bearer {TOK}"}


def get(url, params=None):
    r = requests.get(url, headers=H, params=params or {}, timeout=60)
    return r


def main():
    out = {}
    # 方式1：drive v1 文件评论 API（file_type=docx 必填）
    r = get(f"{OPEN}/drive/v1/files/{DOC}/comments", {"file_type": "docx", "page_size": 100})
    print("== drive/v1 comments:", r.status_code)
    j = r.json()
    print(json.dumps(j, ensure_ascii=False)[:3000])
    out["drive_v1"] = j
    # 分页拉全
    items = (j.get("data") or {}).get("items") or []
    pt = (j.get("data") or {}).get("page_token")
    while (j.get("data") or {}).get("has_more") and pt:
        j = get(f"{OPEN}/drive/v1/files/{DOC}/comments",
                {"file_type": "docx", "page_size": 100, "page_token": pt}).json()
        items += (j.get("data") or {}).get("items") or []
        pt = (j.get("data") or {}).get("page_token")
    print("total comments:", len(items))

    # 逐条拉取回复 + 输出可读文本
    def short(bd):
        return json.dumps(bd, ensure_ascii=False)
    with io.open(os.path.join(os.path.dirname(__file__), "_comments_readable.txt"), "w", encoding="utf-8") as f:
        for it in items:
            f.write("=" * 80 + "\n")
            f.write(f"comment_id: {it.get('comment_id')}  is_solved: {it.get('is_solved')}\n")
            f.write(f"owner: {short(it.get('owner',{}))}\n")
            f.write(f"created: {it.get('create_time')}  replies_count: {len(it.get('replies') or [])}\n")
            f.write("reply_list: " + short(it.get("reply_list")) + "\n")
            for rep in (it.get("reply_list") or []):
                f.write("  reply: " + short(rep) + "\n")
            f.write("whole: " + json.dumps(it, ensure_ascii=False) + "\n\n")
    print("readable -> _comments_readable.txt")
    out["items"] = items

    # 方式2：docx 评论相关（部分版本有 /docx/v1/documents/{id}/comments）
    r2 = get(f"{OPEN}/docx/v1/documents/{DOC}/comments", {"page_size": 100})
    print("\n== docx/v1 comments:", r2.status_code)
    print(r2.text[:800])
    out["docx_v1"] = {"status": r2.status_code, "body": r2.text[:2000]}

    with io.open(os.path.join(os.path.dirname(__file__), "_comments.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nsaved -> _comments.json")


if __name__ == "__main__":
    main()
