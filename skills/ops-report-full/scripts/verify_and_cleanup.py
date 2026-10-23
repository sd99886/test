# -*- coding: utf-8 -*-
"""校验已发布文档的块完整性 + 删除探测遗留文档/表格"""
import json, io, requests, sys

cache = json.load(io.open(".token_cache.json", encoding="utf-8"))
tok = cache["access_token"]
H = {"Authorization": f"Bearer {tok}"}
OPEN = "https://open.feishu.cn/open-apis"


def fetch_all_blocks(doc):
    items, pt = [], None
    while True:
        u = f"{OPEN}/docx/v1/documents/{doc}/blocks?page_size=500"
        if pt:
            u += f"&page_token={pt}"
        r = requests.get(u, headers=H, timeout=60).json()
        assert r["code"] == 0, r
        items += r["data"]["items"]
        if not r["data"].get("has_more"):
            break
        pt = r["data"]["page_token"]
    return items


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if mode == "verify":
        doc = sys.argv[2] if len(sys.argv) > 2 else "YOUR_DOC_ID"
        items = fetch_all_blocks(doc)
        from collections import Counter
        c = Counter(b["block_type"] for b in items)
        print("total blocks:", len(items))
        print("block_type dist:", dict(sorted(c.items())))
        print("images:", c.get(27), "tables:", c.get(31), "cells:", c.get(32))
        links = []
        with io.open("_verify.txt", "w", encoding="utf-8") as out:
            for b in items:
                if b["block_type"] in (2, 4, 5):
                    el = b.get("text") or b.get("heading2") or b.get("heading3")
                    s = "".join(e.get("text_run", {}).get("content", "") for e in el.get("elements", []))
                    out.write(f"[{b['block_type']}] {s}\n")
                    if b["block_type"] == 2:
                        for e in b["text"]["elements"]:
                            st = e.get("text_run", {}).get("text_element_style", {})
                            if st.get("link"):
                                links.append(st["link"]["url"])
        print("links:", links)
        print("dump -> _verify.txt (tail below)")
        with io.open("_verify.txt", encoding="utf-8") as f:
            lines = f.read().splitlines()
        for ln in lines[-6:]:
            print(" ", ln[:120])
    elif mode == "cleanup":
        # 旧版报告文档（新版 RMFQdw8RuotViPxmFyLcprQOnIe 发布并校验通过后删除；用户已确认全删）
        docs = ["AmewdCygQo0XjSxgtqLcApUInSd",   # 第一版（《调整点》修订）
                "CTzpdUkkfoGseFxl2GkcofZyn8f",    # 第二版（10条评论修订）
                "YOUR_DOC_ID"]    # 第三版（本轮评论所在版）
        ss = []
        targets = [(d, "docx") for d in docs] + [(s, "sheet") for s in ss]
        for tk, tp in targets:
            r = requests.delete(f"{OPEN}/drive/v1/files/{tk}?type={tp}", headers=H, timeout=60)
            try:
                j = r.json()
                print(f"del {tp}", tk, "->", r.status_code, j.get("code"), j.get("msg", "")[:80])
            except Exception:
                print(f"del {tp}", tk, "->", r.status_code, r.text[:40])


if __name__ == "__main__":
    main()
