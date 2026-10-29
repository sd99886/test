# -*- coding: utf-8 -*-
"""
退货原因分析 — 飞书电子表格交付脚本
创建 4 Sheet 飞书电子表格：汇总透视 / 分月透视 / 数据明细 / 分析结论

用法：
  python create_feishu.py <csv_path> <analysis_json_path> <title>

凭据从环境变量读取：
  FEISHU_APP_ID      — 飞书应用 App ID
  FEISHU_APP_SECRET  — 飞书应用 App Secret
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

import requests
import json
import math
import pandas as pd

# ── 凭据（从环境变量读取，脱敏版不含硬编码密钥） ────────
APP_ID = os.environ.get("FEISHU_APP_ID", "YOUR_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "YOUR_APP_SECRET")

# ── 原因中文映射 ─────────────────────────────────────────
REASON_CN = {
    "Item Doesn't Fit": "尺码问题",
    "Dislike the Fabric": "面料问题",
    "Arrived Different From Description/Photo": "描述不符",
    "I Don't Like the Product": "不喜欢",
    "Order not shipped, cancelled": "订单取消",
    "Other": "其他",
}

SUB_CN = {
    "Too big": "偏大", "too big": "偏大",
    "Too small": "偏小", "too small": "偏小",
    "Body length too long": "靴筒过长",
    "Not my style": "不喜欢款式",
    "Dislike the design": "不喜欢设计",
    "Fabric is thin/transparent": "面料太薄/透",
    "Cheap material": "材质廉价",
    "Easily wrinkled": "易起皱",
    "Material difference": "材质差异",
    "Order cancellation": "订单取消",
    "Other": "其他",
}

# ── 飞书 API 工具函数 ──────────────────────────────────

def get_token():
    """获取 tenant_access_token"""
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
    )
    return r.json()["tenant_access_token"]


def H(t):
    """构造请求头"""
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def create_ss(t, title):
    """创建电子表格，返回 spreadsheet_token"""
    r = requests.post(
        "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets",
        headers=H(t), json={"title": title},
    )
    return r.json()["data"]["spreadsheet"]["spreadsheet_token"]


def get_sheets(t, ss):
    """获取所有工作表列表"""
    return requests.get(
        f"https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{ss}/sheets/query",
        headers=H(t),
    ).json()["data"]["sheets"]


def rename_sheet(t, ss, sid, title):
    """重命名工作表"""
    requests.patch(
        f"https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{ss}/sheets/{sid}",
        headers=H(t), json={"title": title},
    )


def add_sheet(t, ss, title):
    """添加新工作表，返回 sheet_id"""
    r = requests.post(
        f"https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{ss}/sheets",
        headers=H(t), json={"title": title},
    )
    return r.json()["data"]["sheet"]["sheet_id"]


def write_range(t, ss, sid, values):
    """批量写入数据（自动分批，列数取批次内最大宽度）"""
    if not values:
        return
    max_cols = max(len(row) for row in values if row)

    def cl(n):
        s = ""
        while n > 0:
            n -= 1
            s = chr(65 + n % 26) + s
            n //= 26
        return s

    ec = cl(max_cols)
    batch = 100
    for start in range(0, len(values), batch):
        end = min(start + batch, len(values))
        chunk = values[start:end]
        for i, row in enumerate(chunk):
            for j, v in enumerate(row):
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    chunk[i][j] = ""
                elif isinstance(v, float):
                    chunk[i][j] = round(v, 4)
        rng = f"{sid}!A{start + 1}:{ec}{end}"
        requests.put(
            f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ss}/values",
            headers=H(t),
            json={"valueRange": {"range": rng, "values": chunk}},
        )
    print(f"   写入 {len(values)} 行完成")


def set_style(t, ss, sid, rng, style):
    """设置单元格样式"""
    requests.put(
        f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{ss}/style",
        headers=H(t),
        json={"range": f"{sid}!{rng}", "style": style},
    )


def set_perm(t, ss):
    """设置组织内可访问权限"""
    requests.patch(
        f"https://open.feishu.cn/open-apis/drive/v1/permissions/{ss}/public",
        headers=H(t),
        json={"external_access_entity": "open", "link_share_entity": "tenant_editable"},
        params={"type": "sheet"},
    )


# ── 样式常量 ──────────────────────────────────────────
ST = {
    "TITLE": {
        "backgroundColor": {"red": 0.18, "green": 0.33, "blue": 0.59},
        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
        "bold": True, "fontSize": 12,
    },
    "SEC": {
        "backgroundColor": {"red": 0.84, "green": 0.90, "blue": 0.94},
        "bold": True, "fontSize": 11,
    },
    "HDR": {
        "backgroundColor": {"red": 0.27, "green": 0.45, "blue": 0.77},
        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
        "bold": True, "fontSize": 10,
    },
    "RED": {"backgroundColor": {"red": 1.0, "green": 0.78, "blue": 0.81}},
    "YEL": {"backgroundColor": {"red": 1.0, "green": 0.92, "blue": 0.61}},
    "GRN": {"backgroundColor": {"red": 0.78, "green": 0.94, "blue": 0.81}},
    "SUB": {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.0}, "bold": True},
    "TOT": {"backgroundColor": {"red": 0.85, "green": 0.89, "blue": 0.95}, "bold": True},
}


# ── 主流程 ────────────────────────────────────────────

def main(csv_path, json_path, title):
    """
    创建飞书电子表格，包含 4 个 Sheet。

    参数：
      csv_path  — 原始查询结果 CSV 路径
      json_path — 7 大板块分析结论 JSON 路径
      title     — 电子表格标题
    """
    t = get_token()
    print("1. 创建表格...")
    ss = create_ss(t, title)
    link = f"https://mycupshe.feishu.cn/sheets/{ss}"
    print(f"   {link}")

    # 读取数据
    df = pd.read_csv(csv_path)
    df.rename(columns={c: "GMV" for c in df.columns if c.lower() == "gmv"}, inplace=True)
    for c in ["sku级别一级原因", "sku级别二级原因", "sku级别三级原因"]:
        df[c] = df[c].fillna("").replace("", "\\N")

    # 自动检测月份并映射中文
    months = sorted(df["销售月"].unique())
    month_cn = {}
    for m in months:
        parts = m.split("-")
        if len(parts) == 2:
            month_num = int(parts[1])
            month_cn[m] = f"{month_num}月"
    df["月份"] = df["销售月"].map(month_cn).fillna(df["销售月"])

    sheets = get_sheets(t, ss)
    did = sheets[0]["sheet_id"]

    # ═══ Sheet 1: 汇总透视 ═══
    print("2. 汇总透视...")
    rename_sheet(t, ss, did, "汇总透视")
    sr = df.groupby(["skc", "一级品类", "二级品类", "sku级别一级原因", "sku级别二级原因"]).agg(
        销量=("销量", "sum"), 退款数量=("退款数量", "sum"),
        GMV=("GMV", "sum"), 退款总额=("退款总额", "sum"),
    ).reset_index()
    st = df.groupby("skc").agg(销量=("销量", "sum"), 退款数量=("退款数量", "sum")).reset_index()
    gs = int(df["销量"].sum())
    gr = int(df["退款数量"].sum())

    rows = [[f"{title} — 退货汇总透视"], [],
            ["SKC", "一级原因", "二级原因", "销量", "销量占比", "退款数量", "退款占比", "退件率"]]
    title_r = [1]
    hdr_r = [3]
    sub_r = []
    tot_r = []
    ri = 4
    for _, s in st.sort_values("退款数量", ascending=False).iterrows():
        skc = s["skc"]
        ss_v = int(s["销量"])
        sr_v = int(s["退款数量"])
        sd = sr[sr["skc"] == skc]
        nr = sd[sd["sku级别一级原因"] == "\\N"]
        nrs = int(nr["销量"].sum())
        nrr = int(nr["退款数量"].sum())
        if nrs > 0:
            rows.append([skc, "\\N", "", nrs,
                         round(nrs / ss_v, 4) if ss_v else 0,
                         nrr, round(nrr / sr_v, 4) if sr_v else 0,
                         round(nrr / nrs, 4) if nrs else 0])
            ri += 1
            rows.append(["", "\\N 汇总", "", nrs,
                         round(nrs / ss_v, 4) if ss_v else 0,
                         nrr, round(nrr / sr_v, 4) if sr_v else 0,
                         round(nrr / nrs, 4) if nrs else 0])
            sub_r.append(ri)
            ri += 1
        reasons = sd[sd["sku级别一级原因"] != "\\N"].groupby("sku级别一级原因").agg(
            销量=("销量", "sum"), 退款数量=("退款数量", "sum"),
        ).reset_index().sort_values("退款数量", ascending=False)
        for _, rr in reasons.iterrows():
            r1 = rr["sku级别一级原因"]
            r1s = int(rr["销量"])
            r1r = int(rr["退款数量"])
            subs = sd[sd["sku级别一级原因"] == r1]
            for _, sb in subs.iterrows():
                r2 = sb["sku级别二级原因"]
                s2 = int(sb["销量"])
                r2r = int(sb["退款数量"])
                rows.append(["", r1, r2 if r2 != "\\N" else "", s2,
                             round(s2 / ss_v, 4) if ss_v else 0,
                             r2r, round(r2r / r1r, 4) if r1r else 0,
                             round(r2r / s2, 4) if s2 else 0])
                ri += 1
            rows.append(["", f"{r1} 汇总", "", r1s,
                         round(r1s / ss_v, 4) if ss_v else 0,
                         r1r, round(r1r / sr_v, 4) if sr_v else 0,
                         round(r1r / r1s, 4) if r1s else 0])
            sub_r.append(ri)
            ri += 1
        rows.append([f"{skc} 汇总", "", "", ss_v,
                     round(ss_v / gs, 4) if gs else 0,
                     sr_v, round(sr_v / gr, 4) if gr else 0,
                     round(sr_v / ss_v, 4) if ss_v else 0])
        tot_r.append(ri)
        ri += 1
    rows.append(["总计", "", "", gs, 1.0, gr, 1.0, round(gr / gs, 4) if gs else 0])
    tot_r.append(ri)
    write_range(t, ss, did, rows)
    for r in title_r:
        set_style(t, ss, did, f"A{r}:H{r}", ST["TITLE"])
    for r in hdr_r:
        set_style(t, ss, did, f"A{r}:H{r}", ST["HDR"])
    if sub_r:
        set_style(t, ss, did, ",".join([f"A{r}:H{r}" for r in sub_r[:50]]), ST["SUB"])
    if tot_r:
        set_style(t, ss, did, ",".join([f"A{r}:H{r}" for r in tot_r[:50]]), ST["TOT"])
    print(f"   汇总透视完成 ({ri}行)")

    # ═══ Sheet 2: 分月透视 ═══
    print("3. 分月透视...")
    sid2 = add_sheet(t, ss, "分月透视")
    rows2 = [[f"{title} — 分月退货透视"], [],
             ["月(销售月)", "SKC", "一级原因", "二级原因", "销量", "销量占比", "退款数量", "退款占比"]]
    t2 = [1]
    h2 = [3]
    sb2 = []
    tl2 = []
    r2 = 4
    for month in sorted(df["月份"].unique()):
        md = df[df["月份"] == month]
        ms = int(md["销量"].sum())
        mr = int(md["退款数量"].sum())
        for skc in md["skc"].unique():
            sd = md[md["skc"] == skc]
            ssv = int(sd["销量"].sum())
            srv = int(sd["退款数量"].sum())
            nr = sd[sd["sku级别一级原因"] == "\\N"]
            nrs = int(nr["销量"].sum())
            nrr = int(nr["退款数量"].sum())
            if nrs > 0:
                rows2.append([month, skc, "\\N", "", nrs,
                              round(nrs / ms, 4) if ms else 0,
                              nrr, round(nrr / srv, 4) if srv else 0])
                r2 += 1
                rows2.append(["", "", "\\N 汇总", "", nrs,
                              round(nrs / ms, 4) if ms else 0,
                              nrr, round(nrr / srv, 4) if srv else 0])
                sb2.append(r2)
                r2 += 1
            rd = sd[sd["sku级别一级原因"] != "\\N"]
            for r1 in rd["sku级别一级原因"].unique():
                r1d = rd[rd["sku级别一级原因"] == r1]
                r1r = int(r1d["退款数量"].sum())
                r1s = int(r1d["销量"].sum())
                for _, sr2 in r1d.iterrows():
                    r2n = sr2["sku级别二级原因"]
                    rows2.append(["", "", r1, r2n if r2n != "\\N" else "",
                                  int(sr2["销量"]),
                                  round(sr2["销量"] / ms, 4) if ms else 0,
                                  int(sr2["退款数量"]),
                                  round(sr2["退款数量"] / r1r, 4) if r1r else 0])
                    r2 += 1
                rows2.append(["", "", f"{r1} 汇总", "", r1s,
                              round(r1s / ms, 4) if ms else 0,
                              r1r, round(r1r / srv, 4) if srv else 0])
                sb2.append(r2)
                r2 += 1
            rows2.append(["", f"{skc} 汇总", "", "", ssv,
                          round(ssv / ms, 4) if ms else 0,
                          srv, round(srv / mr, 4) if mr else 0])
            tl2.append(r2)
            r2 += 1
        rows2.append([f"{month} 汇总", "", "", "", ms, 1.0, mr, 1.0])
        tl2.append(r2)
        r2 += 1
    write_range(t, ss, sid2, rows2)
    for r in t2:
        set_style(t, ss, sid2, f"A{r}:H{r}", ST["TITLE"])
    for r in h2:
        set_style(t, ss, sid2, f"A{r}:H{r}", ST["HDR"])
    if sb2:
        set_style(t, ss, sid2, ",".join([f"A{r}:H{r}" for r in sb2[:50]]), ST["SUB"])
    if tl2:
        set_style(t, ss, sid2, ",".join([f"A{r}:H{r}" for r in tl2[:50]]), ST["TOT"])
    print(f"   分月透视完成 ({r2}行)")

    # ═══ Sheet 3: 数据明细 ═══
    print("4. 数据明细...")
    sid3 = add_sheet(t, ss, "数据明细")
    dv = [df.columns.tolist()] + df.values.tolist()
    write_range(t, ss, sid3, dv)
    max_col_letter = "A"
    ncols = len(df.columns)
    if ncols > 0:
        n = ncols
        s = ""
        while n > 0:
            n -= 1
            s = chr(65 + n % 26) + s
            n //= 26
        max_col_letter = s
    set_style(t, ss, sid3, f"A1:{max_col_letter}1", ST["HDR"])
    print(f"   数据明细完成 ({len(dv) - 1}行)")

    # ═══ Sheet 4: 分析结论 ═══
    print("5. 分析结论...")
    sid4 = add_sheet(t, ss, "分析结论")
    with open(json_path, "r", encoding="utf-8") as f:
        a = json.load(f)
    s1 = a["section1_overview"]
    rows4 = []
    t4 = []
    sc4 = []
    hd4 = []
    rd4 = []
    yw4 = []
    gn4 = []

    def at(txt):
        rows4.append([txt])
        t4.append(len(rows4))

    def asc(txt):
        rows4.append([txt])
        sc4.append(len(rows4))

    def ah(cols):
        rows4.append(cols)
        hd4.append(len(rows4))

    def ad(cols, c=None):
        rows4.append(cols)
        if c == "red":
            rd4.append(len(rows4))
        elif c == "yellow":
            yw4.append(len(rows4))
        elif c == "green":
            gn4.append(len(rows4))

    def ae():
        rows4.append([])

    at(f"{title} — 退货分析结论")
    ae()

    # 一、整体退货概况
    asc("一、整体退货概况")
    ah(["指标", "数值"])
    ad(["总销量", f"{s1['总销量']} 件"])
    ad(["总退款数量", f"{s1['总退款数量']} 件"])
    ad(["总 GMV", f"${s1['总GMV(USD)']:,.2f}"])
    ad(["总退款金额", f"${s1['总退款金额(USD)']:,.2f}"])
    c = "yellow" if s1["退件率"] > 10 else None
    ad(["退件率", f"{s1['退件率']}%"], c)
    ad(["退货率", f"{s1['退货率']}%"])
    ae()

    # 二、退货原因分布
    asc("二、退货原因分布（按退款数量排序）")
    ah(["一级原因", "退款数量", "占比", "退款金额", "退件率"])
    for it in a["section2_reason_dist"]:
        cn = REASON_CN.get(it["一级原因"], "")
        nm = f"{it['一级原因']}（{cn}）" if cn else it["一级原因"]
        rv = round(it["退款数量"] / it["销量"] * 100, 2) if it["销量"] > 0 else 0
        c = "red" if it["占比"] >= 20 else None
        ad([nm, it["退款数量"], f"{it['占比']}%", f"${it['退款金额']:,.2f}", f"{rv}%"], c)
    ae()

    asc("退货二级原因 TOP 3")
    ah(["二级原因", "退款数量", "占比例", "退件率"])
    for rn, subs in a["section2_sub_reasons"].items():
        for s in subs:
            cn = SUB_CN.get(s["二级原因"], "")
            nm = f"{s['二级原因']}（{cn}）" if cn else s["二级原因"]
            c = "red" if s["占比"] >= 50 else None
            ad([nm, s["退款数量"], f"{s['占比']}%", ""], c)
    ae()
    tp2 = a["section2_reason_dist"][:2]
    tp2p = sum(x["占比"] for x in tp2)
    rows4.append([f"★ 关键发现：{tp2[0]['一级原因']} + {tp2[1]['一级原因']} 合计占退货的 {tp2p:.1f}%，是核心痛点。"])
    ae()

    # 三、分月退货趋势
    asc("三、分月退货趋势")
    ah(["月份", "销量", "退款数量", "退件率", "趋势判断"])
    for m in a["section3_monthly_trend"]:
        mc = month_cn.get(m["销售月"], m["销售月"])
        tg = m.get("标注", "")
        if "峰值" in tg:
            tr = "退件率最高月"
            c = "red"
        elif "恶化" in tg:
            tr = "环比恶化"
            c = "yellow"
        elif "改善" in tg:
            tr = "环比改善"
            c = "green"
        else:
            tr = "基准月"
            c = None
        ad([mc, m["销量"], m["退款数量"], f"{m['退件率']}%", tr], c)
    ae()

    asc("分月退货原因明细")
    ah(["月份", "主要退货原因", "退款件数", "退件率", "备注"])
    for m in a["section4_monthly_reason"]:
        mc = month_cn.get(m["销售月"], m["销售月"])
        cn = SUB_CN.get(m["一级原因"], "")
        rn = REASON_CN.get(m["一级原因"], "")
        nm = f"{rn}({cn})" if cn and rn else m["一级原因"]
        nt = ""
        if m["退件率"] > 50:
            nt = "集中爆发"
            c = "red"
        elif m["退件率"] > 25:
            nt = "需关注"
            c = "yellow"
        else:
            c = None
        ad([mc, nm, m["退款数量"], f"{m['退件率']}%", nt], c)
    ae()

    # 四、深层问题诊断
    asc("四、深层问题诊断")
    for rn, d in a["section5_diagnosis"].items():
        cn = REASON_CN.get(rn, rn)
        subs = [s for s in d.get("二级原因", []) if s["退款数量"] > 0]
        st = ", ".join([
            f"{SUB_CN.get(s['二级原因'], s['二级原因'])} {s['退款数量']}件({s['占比']}%)"
            for s in subs
        ])
        rows4.append([f"【{cn} — 占退货 {d['占总退款比']}%，{d['严重度']}】"])
        rows4.append([f"  {st}"])
        rows4.append([f"  涉及 {d['涉及销量']} 件销量，退件率 {d['退件率']}%"])
        ae()

    # 五、改善建议
    asc("五、改善建议")
    ah(["优先级", "措施", "具体方案", "预期效果"])
    for pri, ms, pl, ef in a.get("section6_suggestions", [
        ("P0", "调整鞋楦/尺码表", "与工厂沟通调整鞋楦；商品页增加尺码建议", "从根本上解决尺码问题"),
        ("P0", "面料升级/加衬里", "增加内衬或使用更厚实的面料", "提升质感，减少面料类退货"),
        ("P1", "优化产品图", "拍摄实物细节图，展示面料真实质感", "管理客户预期"),
        ("P1", "增加试穿反馈", "引导客户反馈尺码感受", "帮助后续客户选对尺码"),
        ("P1", "周度退货监控", "每周追踪退件率变化", "及时发现问题趋势"),
    ]):
        c = "red" if pri == "P0" else "yellow"
        ad([pri, ms, pl, ef], c)
    ae()

    # 六、改善目标
    asc("六、改善目标")
    ah(["维度", "现状", "目标"])
    tg = a["section7_targets"]
    ml = a["section3_monthly_trend"]
    ad(["整体退件率", f"{tg['current_rate']}%", f"< {tg['target_rate']}%"])
    ad(["TOP1原因占比", f"{a['section2_reason_dist'][0]['占比']}%", "< 20%"])
    ad(["月度趋势", f"峰值月 -> 当前{ml[-1]['退件率']}%", "持续改善"])
    ae()
    ta = tg.get("top_actions", a["section6_suggestions"][:3])
    atxt = "★ 最优先行动项（TOP 3）："
    for i, x in enumerate(ta[:3], 1):
        atxt += f"\n{i}. [{x.get('优先级', 'P0')}] {x['原因']} -> {x['建议方向']}"
    rows4.append([atxt])

    write_range(t, ss, sid4, rows4)
    for r in t4:
        set_style(t, ss, sid4, f"A{r}:E{r}", ST["TITLE"])
    for r in sc4:
        set_style(t, ss, sid4, f"A{r}:E{r}", ST["SEC"])
    for r in hd4:
        set_style(t, ss, sid4, f"A{r}:E{r}", ST["HDR"])
    if rd4:
        set_style(t, ss, sid4, ",".join([f"A{r}:E{r}" for r in rd4[:50]]), ST["RED"])
    if yw4:
        set_style(t, ss, sid4, ",".join([f"A{r}:E{r}" for r in yw4[:50]]), ST["YEL"])
    if gn4:
        set_style(t, ss, sid4, ",".join([f"A{r}:E{r}" for r in gn4[:50]]), ST["GRN"])
    print(f"   分析结论完成 ({len(rows4)}行)")

    # 设置权限
    print("6. 设置权限...")
    set_perm(t, ss)

    print(f"\n{'=' * 60}")
    print(f"完成! 链接: {link}")
    print(f"4个Sheet: 汇总透视 | 分月透视 | 数据明细 | 分析结论")
    print(f"{'=' * 60}")
    return link


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python create_feishu.py <csv_path> <analysis_json_path> <title>")
        print("环境变量: FEISHU_APP_ID, FEISHU_APP_SECRET")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
