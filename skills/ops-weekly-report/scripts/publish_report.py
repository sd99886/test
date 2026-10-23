# -*- coding: utf-8 -*-
"""发布经营分析报告到飞书：
1. 创建电子表格《品类拆解全量明细》并写入 L2(70x115)/L3(242x116) 全量明细（所有列，一列不漏）；
2. 创建飞书文档并按 feishu_report.json 的 CONTENT 顺序写入：标题/文本/descendant 表格/图片(三步法)/链接；
3. 输出文档与电子表格 URL。

已验证的 API 约定（见 probe_feishu3~6）：
- 表格：descendant API，block_type=31，children(cell id 列表)放块顶层，cell=32 内挂 text=2；实测一次 541 blocks 成功；
- 图片：① 建空 image block(27, token='') → ② drive/v1/medias/upload_all(multipart form, parent_type=docx_image, parent_node=图片块ID) → ③ PATCH blocks/{id} replace_image；
- 电子表格写入：V2 PUT /sheets/v2/spreadsheets/{token}/values（V3 values 路径不存在）。
"""
import argparse, csv, io, json, os, sys, time, requests

BASE = os.environ.get("OPS_BASE") or os.getcwd()  # 工作区根目录（可用环境变量 OPS_BASE 覆盖）
FEISHU = os.path.join(BASE, "feishu_api")
OPEN = "https://open.feishu.cn/open-apis"

# ================= 运行参数 =================
_ap = argparse.ArgumentParser(description="发布经营分析报告到飞书（文档 + 可选电子表格）")
_ap.add_argument("--report-json", default=os.path.join(BASE, r"out\ops_20261021\feishu_report.json"),
                 help="gen_report_json.py 产出的 feishu_report.json 路径")
_ap.add_argument("--reuse-sheet", default="",
                 help="复用的电子表格 token（传空字符串则新建，仅当报告含第 4 章品类拆解时才需要）")
ARGS = _ap.parse_args()
REPORT_JSON = ARGS.report_json
OUT = os.path.dirname(REPORT_JSON)          # 产物目录与数据目录一致

MAX_TABLE_CELLS = 470          # descendant 一次建表的安全上限（实测块数上限约1000：450 cells/946 blocks 成功、500 cells/1051 blocks 失败；块数≈cells×2+1）
CHILDREN_BATCH = 50            # 普通块每批追加数量


# ---------------- token ----------------
def load_token():
    cache_path = os.path.join(FEISHU, ".token_cache.json")
    if os.path.exists(cache_path):
        try:
            cache = json.load(io.open(cache_path, encoding="utf-8"))
            if cache.get("access_token") and cache.get("expires_at", 0) > time.time() + 900:
                return cache["access_token"]
            print("[Token 缓存] 已过期，重新授权")
        except Exception:
            print("[Token 缓存] 读取失败，重新授权")
    else:
        print("[Token 缓存] 不存在，走 OAuth 授权")
    sys.path.insert(0, FEISHU)
    from feishu_chat_reader import get_user_access_token
    tok = get_user_access_token()  # 走 OAuth 浏览器授权并刷新缓存
    return tok


TOK = load_token()


# 应用身份 token（懒加载）：新建电子表格时用应用身份创建，应用即 owner，
# 可直接设置链接分享权限并把授权用户加为协作者（无需用户身份 drive 系 scope）
TOK_TENANT = None
SHEET_TOK = None  # 电子表格操作当前使用的 token（新建=应用身份；复用旧表=用户身份）


def get_tenant_token():
    global TOK_TENANT
    if not TOK_TENANT:
        from config import APP_ID, APP_SECRET
        r = requests.post(f"{OPEN}/auth/v3/tenant_access_token/internal",
                          json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=30)
        j = r.json()
        assert j.get("tenant_access_token"), f"获取 tenant_access_token 失败: {j}"
        TOK_TENANT = j["tenant_access_token"]
    return TOK_TENANT


def sheet_api(method, url, **kw):
    """电子表格专用请求：token 由 SHEET_TOK 决定（新建表=应用身份/复用表=用户身份）"""
    headers = {"Authorization": f"Bearer {SHEET_TOK or TOK}"}
    headers.update(kw.pop("headers", {}))
    return requests.request(method, url, headers=headers, timeout=300, **kw)


def sheet_api_json(method, url, payload=None, params=None):
    kw = {"headers": {"Content-Type": "application/json"}}
    if payload is not None:
        kw["json"] = payload
    if params is not None:
        kw["params"] = params
    r = sheet_api(method, url, **kw)
    try:
        j = r.json()
    except Exception:
        raise RuntimeError(f"{method} {url} -> HTTP {r.status_code} non-json: {r.text[:200]}")
    if j.get("code") != 0:
        raise RuntimeError(f"{method} {url} -> HTTP {r.status_code} code={j.get('code')} {j.get('msg','')[:200]}")
    return j


def api(method, url, **kw):
    headers = {"Authorization": f"Bearer {TOK}"}
    headers.update(kw.pop("headers", {}))
    r = requests.request(method, url, headers=headers, timeout=300, **kw)
    return r


def api_json(method, url, payload=None, params=None):
    kw = {"headers": {"Content-Type": "application/json"}}
    if payload is not None:
        kw["json"] = payload
    if params is not None:
        kw["params"] = params
    r = api(method, url, **kw)
    try:
        j = r.json()
    except Exception:
        raise RuntimeError(f"{method} {url} -> HTTP {r.status_code} non-json: {r.text[:200]}")
    if j.get("code") != 0:
        raise RuntimeError(f"{method} {url} -> HTTP {r.status_code} code={j.get('code')} {j.get('msg','')[:200]}")
    return j


# ---------------- 电子表格 ----------------
def col_letter(n):
    s = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


def to_val(s):
    if s is None:
        return ""
    s2 = s.strip() if isinstance(s, str) else s
    if s2 == "" or s2 is None:
        return ""
    try:
        return float(s2)
    except (TypeError, ValueError):
        return s


def create_spreadsheet(title):
    j = sheet_api_json("POST", f"{OPEN}/sheets/v3/spreadsheets", {"title": title})
    return j["data"]["spreadsheet"]["spreadsheet_token"]


def query_sheets(ss):
    j = sheet_api_json("GET", f"{OPEN}/sheets/v3/spreadsheets/{ss}/sheets/query")
    data = j.get("data", {})
    items = data.get("sheets") or data.get("items") or []
    out = []
    for it in items:
        sid = it.get("sheet_id") or it.get("sheetId")
        if sid:
            out.append((sid, it.get("title", "")))
    return out


def setup_two_sheets(ss, name1, name2):
    """把默认工作表改名为 name1，并新增 name2。返回 [(sheet_id1,name1),(sheet_id2,name2)]"""
    sheets = query_sheets(ss)
    assert sheets, "新建电子表格后未查到任何工作表"
    first_id, _ = sheets[0]
    second_id = None
    payload = {"requests": [
        {"updateSheet": {"properties": {"sheetId": first_id, "title": name1}}},
        {"addSheet": {"properties": {"title": name2}}},
    ]}
    r = sheet_api("PUT", f"{OPEN}/sheets/v2/spreadsheets/{ss}/sheets_batch_update",
                  headers={"Content-Type": "application/json"}, json=payload)
    try:
        j = r.json()
        if j.get("code") == 0:
            for rep in j["data"].get("replies", []):
                add = rep.get("addSheet")
                if add:
                    props = add.get("properties", {})
                    second_id = props.get("sheetId") or props.get("sheet_id")
    except Exception:
        pass
    if not second_id:
        # 回退：V3 建表
        j2 = sheet_api_json("POST", f"{OPEN}/sheets/v3/spreadsheets/{ss}/sheets", {"title": name2})
        d = j2.get("data", {})
        second_id = (d.get("sheet") or d).get("sheet_id") or (d.get("sheet") or d).get("sheetId")
        assert second_id, f"V3 建表返回结构异常: {json.dumps(j2, ensure_ascii=False)[:300]}"
    return [(first_id, name1), (second_id, name2)]


def ensure_sheet1_title(ss, title):
    """幂等：把电子表格第一个工作表改名为 title（评论10：sheet1 改名「二级品类明细」）"""
    sheets = query_sheets(ss)
    if not sheets:
        return
    sid, cur = sheets[0]
    if cur == title:
        print(f"   sheet1 已名为「{title}」，无需改名")
        return
    payload = {"requests": [{"updateSheet": {"properties": {"sheetId": sid, "title": title}}}]}
    sheet_api("PUT", f"{OPEN}/sheets/v2/spreadsheets/{ss}/sheets_batch_update",
              headers={"Content-Type": "application/json"}, json=payload)
    print(f"   sheet1 改名：{cur} -> {title}")


def _get_tenant_token():
    """兼容旧调用：返回应用身份 token"""
    return get_tenant_token()


def get_my_open_id():
    """当前授权用户的 open_id（user token 基础权限即可）"""
    r = api("GET", f"{OPEN}/authen/v1/user_info")
    j = r.json()
    assert j.get("code") == 0, f"获取用户信息失败: {j}"
    return j["data"]["open_id"]


def ensure_user_collaborator(ss, perm="edit"):
    """幂等：应用身份把当前授权用户加为电子表格协作者（应用 owner 的表，用户保留编辑权）"""
    my_id = get_my_open_id()
    r = sheet_api("GET", f"{OPEN}/drive/v1/permissions/{ss}/members",
                  params={"type": "sheet", "page_size": 100})
    try:
        for m in r.json().get("data", {}).get("items", []):
            if m.get("member_id") == my_id and m.get("perm") in (perm, "full_access"):
                print(f"   用户已是该表协作者（{m.get('perm')}），无需添加")
                return
    except Exception:
        pass
    sheet_api_json("POST", f"{OPEN}/drive/v1/permissions/{ss}/members",
                   {"member_type": "openid", "member_id": my_id, "perm": perm},
                   params={"type": "sheet"})
    print(f"   已把授权用户加为协作者（{perm}）")


def ensure_sheet_share(ss, link_share_entity="tenant_readable"):
    """幂等：把电子表格链接分享权限设为「组织内获得链接的人可阅读」。
    新建表（应用 owner）用应用身份写入；复用旧表（用户 owner）先试用户身份、
    再降级应用身份读取校验；异常仅告警不阻断发布。"""
    cur = None
    try:
        j = sheet_api_json("GET", f"{OPEN}/drive/v1/permissions/{ss}/public", params={"type": "sheet"})
        cur = j.get("data", {}).get("permission_public", {}).get("link_share_entity")
    except Exception as e:
        print(f"   [warn] 读取权限设置失败：{str(e)[:120]}")
    if cur is None:
        # 降级：应用身份读取（复用旧表且应用已被添加为协作者时可成功）
        try:
            tt = get_tenant_token()
            r = requests.get(f"{OPEN}/drive/v1/permissions/{ss}/public", params={"type": "sheet"},
                             headers={"Authorization": f"Bearer {tt}"}, timeout=30)
            if r.status_code == 200 and r.json().get("code") == 0:
                cur = r.json()["data"]["permission_public"]["link_share_entity"]
        except Exception as e:
            print(f"   [warn] 应用身份读取权限设置失败：{str(e)[:120]}")
    if cur == link_share_entity:
        print("   链接分享已是「组织内获得链接的人可阅读」，无需修改")
        return
    # 需要写入：优先当前 sheet token，失败再试应用身份
    ok = False
    try:
        sheet_api_json("PATCH", f"{OPEN}/drive/v1/permissions/{ss}/public",
                       {"link_share_entity": link_share_entity}, params={"type": "sheet"})
        ok = True
    except Exception as e:
        print(f"   [warn] 写入权限设置失败（{str(e)[:100]}），尝试应用身份…")
    if not ok:
        try:
            tt = get_tenant_token()
            r = requests.patch(f"{OPEN}/drive/v1/permissions/{ss}/public", params={"type": "sheet"},
                               headers={"Authorization": f"Bearer {tt}", "Content-Type": "application/json"},
                               json={"link_share_entity": link_share_entity}, timeout=30)
            j = r.json()
            if j.get("code") == 0:
                ok = True
            else:
                print(f"   [warn] 应用身份写入失败：code={j.get('code')} {j.get('msg','')[:100]}")
        except Exception as e:
            print(f"   [warn] 应用身份写入权限设置失败：{str(e)[:120]}")
    if ok:
        print(f"   链接分享权限：{cur} -> 组织内获得链接的人可阅读")
    else:
        print("   请在飞书客户端手动设置：电子表格 → 右上角「分享」→ 链接分享 → 组织内获得链接的人可阅读")


def write_csv_to_sheet(ss, sheet_id, csv_path, chunk_cols=40, chunk_rows=400):
    with io.open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows, f"{csv_path} 为空"
    n_rows, n_cols = len(rows), max(len(r) for r in rows)
    # 补齐每行长度
    rows = [r + [""] * (n_cols - len(r)) for r in rows]
    total_cells = 0
    for c0 in range(0, n_cols, chunk_cols):
        c1 = min(c0 + chunk_cols, n_cols)
        for r0 in range(0, n_rows, chunk_rows):
            r1 = min(r0 + chunk_rows, n_rows)
            values = [[to_val(row[i]) for i in range(c0, c1)] for row in rows[r0:r1]]
            rng = f"{sheet_id}!{col_letter(c0+1)}{r0+1}:{col_letter(c1)}{r1}"
            j = sheet_api_json("PUT", f"{OPEN}/sheets/v2/spreadsheets/{ss}/values",
                               {"valueRange": {"range": rng, "values": values}})
            total_cells += int(j.get("data", {}).get("updatedCells", 0))
            time.sleep(0.3)
    return n_rows, n_cols, total_cells


# ---------------- 文档 ----------------
def text_block(s, url=None):
    run = {"text_run": {"content": s or " "}}
    if url:
        run["text_run"]["text_element_style"] = {"link": {"url": url}}
    return {"block_type": 2, "text": {"elements": [run]}}


def heading_block(level, s):
    key = f"heading{level}"
    return {"block_type": {2: 4, 3: 5}[level], key: {"elements": [{"text_run": {"content": s}}]}}


def create_doc(title):
    j = api_json("POST", f"{OPEN}/docx/v1/documents", {"title": title})
    doc_id = j["data"]["document"]["document_id"]
    j2 = api_json("GET", f"{OPEN}/docx/v1/documents/{doc_id}/blocks")
    page_id = j2["data"]["items"][0]["block_id"]
    return doc_id, page_id


def append_children(doc_id, page_id, blocks):
    for i in range(0, len(blocks), CHILDREN_BATCH):
        api_json("POST", f"{OPEN}/docx/v1/documents/{doc_id}/blocks/{page_id}/children",
                 {"children": blocks[i:i + CHILDREN_BATCH]})
        time.sleep(0.2)


def append_table(doc_id, page_id, header, rows):
    """descendant 一次建含内容表格；超过 MAX_TABLE_CELLS 自动按行分块（每块重复表头）。"""
    ncols = len(header)
    max_data_rows = max(1, MAX_TABLE_CELLS // ncols - 1)
    chunks = [rows[i:i + max_data_rows] for i in range(0, len(rows), max_data_rows)] or [[]]
    for k, chunk in enumerate(chunks):
        body = [header] + [[("" if c is None else str(c)) or "-" for c in r] for r in chunk]
        R, C = len(body), ncols
        tb_id = "tbx"
        desc = [{"block_id": tb_id, "block_type": 31,
                 "table": {"property": {"row_size": R, "column_size": C}},
                 "children": [f"cl{ri}_{ci}" for ri in range(R) for ci in range(C)]}]
        for ri in range(R):
            for ci in range(C):
                cid = f"cl{ri}_{ci}"
                tid = f"tx{ri}_{ci}"
                desc.append({"block_id": cid, "block_type": 32, "table_cell": {}, "children": [tid]})
                desc.append({"block_id": tid, "block_type": 2,
                             "text": {"elements": [{"text_run": {"content": body[ri][ci] or "-"}}]},
                             "children": []})
        api_json("POST",
                 f"{OPEN}/docx/v1/documents/{doc_id}/blocks/{page_id}/descendant?document_revision_id=-1",
                 {"index": 0, "children_id": [tb_id], "descendants": desc})
        time.sleep(0.3)
    return len(chunks)


def append_image(doc_id, page_id, path):
    """图片三步法（已验证）。"""
    j = api_json("POST", f"{OPEN}/docx/v1/documents/{doc_id}/blocks/{page_id}/children",
                 {"children": [{"block_type": 27, "image": {"token": ""}}]})
    blk_id = j["data"]["children"][0]["block_id"]
    size = os.path.getsize(path)
    with io.open(path, "rb") as f:
        r = api("POST",
                f"{OPEN}/drive/v1/medias/upload_all?parent_type=docx_image&parent_node={blk_id}&size={size}&extra=",
                data={"file_name": os.path.basename(path), "parent_type": "docx_image",
                      "parent_node": blk_id, "size": str(size)},
                files={"file": (os.path.basename(path), f, "image/png")})
    j2 = r.json()
    if j2.get("code") != 0:
        raise RuntimeError(f"图片上传失败 {path}: {j2}")
    ft = j2["data"]["file_token"]
    api_json("PATCH", f"{OPEN}/docx/v1/documents/{doc_id}/blocks/{blk_id}",
             {"replace_image": {"token": ft}, "document_revision_id": -1})
    time.sleep(0.2)
    return blk_id


# ---------------- 主流程 ----------------
# L2/L3 全量明细内容未变时复用已发布电子表格（避免每次发布遗留重复表格）；
# 传 --reuse-sheet "" 可强制新建。仅当报告含第 4 章品类拆解（include_sheets）时才处理电子表格。
REUSE_SHEET = ARGS.reuse_sheet

def main():
    report = json.load(io.open(REPORT_JSON, encoding="utf-8"))
    title = report["title"]
    content = report["content"]
    include_sheets = report.get("include_sheets", True)

    print("== 1. 电子表格（全量明细）==")
    sheet_url = ""
    if not include_sheets:
        print("   报告不含第 4 章品类拆解（--sections 1237），跳过电子表格")
    else:
        global SHEET_TOK
        if REUSE_SHEET:
            SHEET_TOK = TOK  # 复用旧表：用户身份创建，应用非协作者，继续用用户身份操作
            ss = REUSE_SHEET
            ensure_sheet1_title(ss, "二级品类明细")   # 评论10
            ensure_sheet_share(ss)                     # 链接分享：组织内获得链接的人可阅读
            print("   复用已发布电子表格:", ss)
        else:
            SHEET_TOK = get_tenant_token()  # 新建表：应用身份创建，应用即 owner（自动含「文档应用」）
            ss = create_spreadsheet("品类拆解全量明细（" + report["meta"]["start"] + "~" + report["meta"]["end"] + "）")
            print("   新建电子表格（应用身份，owner=机器人应用）:", ss)
            sheets = setup_two_sheets(ss, report["detail_sheets"][0]["name"], report["detail_sheets"][1]["name"])
            for (sid, name), meta in zip(sheets, report["detail_sheets"]):
                nr, nc, cells = write_csv_to_sheet(ss, sid, meta["csv"])
                print(f"   {name}: 写入 {nr} 行 x {nc} 列 (updatedCells={cells})")
                assert nr - 1 == meta["rows"], f"{name} 行数与预期不符: {nr-1} != {meta['rows']}"
            ensure_user_collaborator(ss)               # 把授权用户加为协作者（保留编辑权）
            ensure_sheet_share(ss)                     # 链接分享：组织内获得链接的人可阅读
        sheet_url = f"https://<your-tenant>.feishu.cn/sheets/{ss}"
        print("   sheet:", sheet_url)

    print("== 2. 创建飞书文档并写入内容 ==")
    doc_id, page_id = create_doc(title)
    doc_url = f"https://<your-tenant>.feishu.cn/docx/{doc_id}"
    print("   doc:", doc_url)

    n_text = n_table = n_image = n_link = 0
    pending = []          # 普通（text/heading/link）块缓冲，攒批提交
    def flush():
        nonlocal pending
        if pending:
            append_children(doc_id, page_id, pending)
            pending = []

    for item in content:
        kind = item["kind"]
        if kind == "h2":
            flush(); append_children(doc_id, page_id, [heading_block(2, item["text"])])
        elif kind == "h3":
            flush(); append_children(doc_id, page_id, [heading_block(3, item["text"])])
        elif kind == "text":
            pending.append(text_block(item["text"])); n_text += 1
        elif kind == "link":
            url = item["url"].replace("{{SHEET_L2_URL}}", sheet_url)
            pending.append(text_block(f"{item['text']}：{url}", url=url)); n_link += 1
        elif kind == "image":
            flush()
            append_image(doc_id, page_id, item["path"])
            if item.get("caption"):
                append_children(doc_id, page_id, [text_block(item["caption"])])
            n_image += 1
        elif kind == "table":
            flush()
            chunks = append_table(doc_id, page_id, item["header"], item["rows"])
            if item.get("note"):
                suffix = "" if chunks == 1 else f"（分 {chunks} 段展示，全部 {len(item['rows'])} 行）"
                append_children(doc_id, page_id, [text_block(item["note"] + suffix)])
            n_table += chunks
        else:
            raise ValueError(f"未知内容类型: {kind}")
    flush()

    print(f"   完成：文本 {n_text}、表格 {n_table} 段、图片 {n_image}、链接 {n_link}")

    # 校验：读回块数量
    j = api_json("GET", f"{OPEN}/docx/v1/documents/{doc_id}/blocks", params={"page_size": 500})
    print("   文档顶层块数（page_size=500 视角）:", len(j["data"].get("items", [])))

    result = {"doc_url": doc_url, "sheet_url": sheet_url, "doc_id": doc_id,
              "spreadsheet_token": (ss if include_sheets else "")}
    with io.open(os.path.join(OUT, "publish_result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("saved ->", os.path.join(OUT, "publish_result.json"))
    print("DOC :", doc_url)
    print("SHEET:", sheet_url)


if __name__ == "__main__":
    main()
