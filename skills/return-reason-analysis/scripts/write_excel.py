# -*- coding: utf-8 -*-
"""
退货原因分析 — Excel / 飞书 4-Sheet 输出工具
生成：汇总透视 + 分月透视 + 数据明细 + 分析结论

用法:
  python write_excel.py <csv_path> <json_path> <output_path>
  或作为模块导入: from write_excel import build_excel
"""
import os, sys, json, math
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── 样式常量 ──
DARK_BLUE_FILL = PatternFill(start_color="FF2F5496", end_color="FF2F5496", fill_type="solid")
SECTION_FILL   = PatternFill(start_color="FFD6E4F0", end_color="FFD6E4F0", fill_type="solid")
HEADER_FILL    = PatternFill(start_color="FF4472C4", end_color="FF4472C4", fill_type="solid")
RED_FILL       = PatternFill(start_color="FFFFC7CE", end_color="FFFFC7CE", fill_type="solid")
YELLOW_FILL    = PatternFill(start_color="FFFFEB9C", end_color="FFFFEB9C", fill_type="solid")
GREEN_FILL     = PatternFill(start_color="FFC6EFCE", end_color="FFC6EFCE", fill_type="solid")
SUBTOTAL_FILL  = PatternFill(start_color="FFFFFF00", end_color="FFFFFF00", fill_type="solid")
TOTAL_FILL     = PatternFill(start_color="FFD9E2F3", end_color="FFD9E2F3", fill_type="solid")
WHITE_FONT     = Font(color="FFFFFFFF", bold=True, size=11)
BOLD_FONT      = Font(bold=True, size=11)
NORMAL_FONT    = Font(size=10)
THIN_BORDER    = Border(
    left=Side(style='thin', color='FFD0D0D0'), right=Side(style='thin', color='FFD0D0D0'),
    top=Side(style='thin', color='FFD0D0D0'), bottom=Side(style='thin', color='FFD0D0D0'))

# ── 原因中文映射 ──
REASON_CN = {
    "Item Doesn't Fit": "尺码问题", "Dislike the Fabric": "面料问题",
    "Arrived Different From Description/Photo": "描述不符",
    "I Don't Like the Product": "不喜欢", "Order not shipped, cancelled": "订单取消", "Other": "其他",
}
SUB_CN = {
    "Too big": "偏大", "too big": "偏大", "Too small": "偏小", "too small": "偏小",
    "Body length too long": "靴筒过长", "Not my style": "不喜欢款式",
    "Dislike the design": "不喜欢设计", "Fabric is thin/transparent": "面料太薄/透",
    "Cheap material": "材质廉价", "Easily wrinkled": "易起皱",
    "Material difference": "材质差异", "Order cancellation": "订单取消", "Other": "其他",
}
MONTH_CN = {'2026-08': '8月', '2026-09': '9月', '2026-10': '10月'}

def r_cn(en): 
    cn = REASON_CN.get(en, ""); return f"{en}（{cn}）" if cn else en
def s_cn(en):
    cn = SUB_CN.get(en, ""); return f"{en}（{cn}）" if cn else en

def _style_cell(cell, fill=None, font=None, border=True, align=None):
    if fill: cell.fill = fill
    if font: cell.font = font
    if border: cell.border = THIN_BORDER
    if align: cell.alignment = align
    elif border: cell.alignment = Alignment(vertical='center', wrap_text=True)

def _write_row(ws, row, values, fill=None, font=None):
    for j, v in enumerate(values, 1):
        c = ws.cell(row=row, column=j, value=v)
        _style_cell(c, fill=fill, font=font or NORMAL_FONT)

def _auto_width(ws, min_w=10, max_w=40):
    for col in ws.columns:
        mx = max((min(len(str(c.value or '')), max_w) for c in col), default=0)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(mx + 2, min_w)

# ══════════════════════════════════════════
def build_excel(csv_path, json_path, output_path):
    """生成 4-Sheet Excel"""
    df = pd.read_csv(csv_path)
    df.rename(columns={c: 'GMV' for c in df.columns if c.lower() == 'gmv'}, inplace=True)
    for c in ['sku级别一级原因', 'sku级别二级原因', 'sku级别三级原因']:
        df[c] = df[c].fillna('').replace('', '\\N')
    df['月份'] = df['销售月'].map(MONTH_CN).fillna(df['销售月'])
    with open(json_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    wb = Workbook()

    # ═══ Sheet 1: 汇总透视 ═══
    ws1 = wb.active; ws1.title = "汇总透视"
    sr = df.groupby(['skc','一级品类','二级品类','sku级别一级原因','sku级别二级原因']).agg(
        销量=('销量','sum'), 退款数量=('退款数量','sum'), GMV=('GMV','sum'), 退款总额=('退款总额','sum')).reset_index()
    st = df.groupby('skc').agg(销量=('销量','sum'), 退款数量=('退款数量','sum')).reset_index()
    gs = int(df['销量'].sum()); gr = int(df['退款数量'].sum())

    ws1.merge_cells("A1:H1")
    c = ws1.cell(row=1, column=1, value="ACC 退货汇总透视"); c.fill = DARK_BLUE_FILL; c.font = WHITE_FONT
    hdrs = ["SKC","一级原因","二级原因","销量","销量占比","退款数量","退款占比","退件率"]
    for j, h in enumerate(hdrs, 1):
        c = ws1.cell(row=3, column=j, value=h); c.fill = HEADER_FILL; c.font = WHITE_FONT; c.border = THIN_BORDER
    r = 4
    for _, s in st.sort_values('退款数量', ascending=False).iterrows():
        skc = s['skc']; ss_v = int(s['销量']); sr_v = int(s['退款数量'])
        sd = sr[sr['skc'] == skc]
        # 无原因
        nr = sd[sd['sku级别一级原因'] == '\\N']; nrs = int(nr['销量'].sum()); nrr = int(nr['退款数量'].sum())
        if nrs > 0:
            _write_row(ws1, r, [skc,'\\N','',nrs,round(nrs/ss_v,4) if ss_v else 0,nrr,round(nrr/sr_v,4) if sr_v else 0,round(nrr/nrs,4) if nrs else 0]); r+=1
            _write_row(ws1, r, ['','\\N 汇总','',nrs,round(nrs/ss_v,4) if ss_v else 0,nrr,round(nrr/sr_v,4) if sr_v else 0,round(nrr/nrs,4) if nrs else 0], SUBTOTAL_FILL, BOLD_FONT); r+=1
        reasons = sd[sd['sku级别一级原因']!='\\N'].groupby('sku级别一级原因').agg(销量=('销量','sum'),退款数量=('退款数量','sum')).reset_index().sort_values('退款数量',ascending=False)
        for _, rr in reasons.iterrows():
            r1 = rr['sku级别一级原因']; r1s = int(rr['销量']); r1r = int(rr['退款数量'])
            for _, sb in sd[sd['sku级别一级原因']==r1].iterrows():
                r2 = sb['sku级别二级原因']; s2 = int(sb['销量']); r2r = int(sb['退款数量'])
                _write_row(ws1, r, ['',r1,r2 if r2!='\\N' else '',s2,round(s2/ss_v,4) if ss_v else 0,r2r,round(r2r/r1r,4) if r1r else 0,round(r2r/s2,4) if s2 else 0]); r+=1
            _write_row(ws1, r, ['',f"{r1} 汇总",'',r1s,round(r1s/ss_v,4) if ss_v else 0,r1r,round(r1r/sr_v,4) if sr_v else 0,round(r1r/r1s,4) if r1s else 0], SUBTOTAL_FILL, BOLD_FONT); r+=1
        _write_row(ws1, r, [f"{skc} 汇总",'','',ss_v,round(ss_v/gs,4) if gs else 0,sr_v,round(sr_v/gr,4) if gr else 0,round(sr_v/ss_v,4) if ss_v else 0], TOTAL_FILL, BOLD_FONT); r+=1
    _write_row(ws1, r, ["总计",'','',gs,1.0,gr,1.0,round(gr/gs,4) if gs else 0], TOTAL_FILL, BOLD_FONT)
    _auto_width(ws1)

    # ═══ Sheet 2: 分月透视 ═══
    ws2 = wb.create_sheet("分月透视")
    ws2.merge_cells("A1:H1")
    c = ws2.cell(row=1, column=1, value="ACC 分月退货透视"); c.fill = DARK_BLUE_FILL; c.font = WHITE_FONT
    for j, h in enumerate(["月(销售月)","SKC","一级原因","二级原因","销量","销量占比","退款数量","退款占比"], 1):
        c = ws2.cell(row=3, column=j, value=h); c.fill = HEADER_FILL; c.font = WHITE_FONT; c.border = THIN_BORDER
    r = 4
    for month in ['8月','9月','10月']:
        md = df[df['月份']==month]; ms = int(md['销量'].sum()); mr = int(md['退款数量'].sum())
        for skc in md['skc'].unique():
            sd = md[md['skc']==skc]; ssv = int(sd['销量'].sum()); srv = int(sd['退款数量'].sum())
            nr = sd[sd['sku级别一级原因']=='\\N']; nrs = int(nr['销量'].sum()); nrr = int(nr['退款数量'].sum())
            if nrs > 0:
                _write_row(ws2, r, [month,skc,'\\N','',nrs,round(nrs/ms,4) if ms else 0,nrr,round(nrr/srv,4) if srv else 0]); r+=1
                _write_row(ws2, r, ['','','\\N 汇总','',nrs,round(nrs/ms,4) if ms else 0,nrr,round(nrr/srv,4) if srv else 0], SUBTOTAL_FILL, BOLD_FONT); r+=1
            rd = sd[sd['sku级别一级原因']!='\\N']
            for r1 in rd['sku级别一级原因'].unique():
                r1d = rd[rd['sku级别一级原因']==r1]; r1r = int(r1d['退款数量'].sum()); r1s = int(r1d['销量'].sum())
                for _, sr2 in r1d.iterrows():
                    r2n = sr2['sku级别二级原因']
                    _write_row(ws2, r, ['','',r1,r2n if r2n!='\\N' else '',int(sr2['销量']),round(sr2['销量']/ms,4) if ms else 0,int(sr2['退款数量']),round(sr2['退款数量']/r1r,4) if r1r else 0]); r+=1
                _write_row(ws2, r, ['','',f"{r1} 汇总",'',r1s,round(r1s/ms,4) if ms else 0,r1r,round(r1r/srv,4) if srv else 0], SUBTOTAL_FILL, BOLD_FONT); r+=1
            _write_row(ws2, r, ['',f"{skc} 汇总",'','',ssv,round(ssv/ms,4) if ms else 0,srv,round(srv/mr,4) if mr else 0], TOTAL_FILL, BOLD_FONT); r+=1
        _write_row(ws2, r, [f"{month} 汇总",'','','',ms,1.0,mr,1.0], TOTAL_FILL, BOLD_FONT); r+=1
    _auto_width(ws2)

    # ═══ Sheet 3: 数据明细 ═══
    ws3 = wb.create_sheet("数据明细")
    for j, col_name in enumerate(df.columns, 1):
        c = ws3.cell(row=1, column=j, value=col_name); c.fill = HEADER_FILL; c.font = WHITE_FONT; c.border = THIN_BORDER
    for i, (_, rd) in enumerate(df.iterrows(), 2):
        for j, v in enumerate(rd, 1):
            c = ws3.cell(row=i, column=j, value=v if pd.notna(v) else ''); c.font = NORMAL_FONT; c.border = THIN_BORDER
    _auto_width(ws3)

    # ═══ Sheet 4: 分析结论 ═══
    ws4 = wb.create_sheet("分析结论")
    s1 = analysis["section1_overview"]; r = 1
    def title(txt):
        nonlocal r; ws4.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        c = ws4.cell(row=r, column=1, value=txt); c.fill = DARK_BLUE_FILL; c.font = WHITE_FONT; r+=1
    def section(txt):
        nonlocal r; ws4.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        c = ws4.cell(row=r, column=1, value=txt); c.fill = SECTION_FILL; c.font = BOLD_FONT; r+=1
    def header(cols):
        nonlocal r
        for j, v in enumerate(cols, 1):
            c = ws4.cell(row=r, column=j, value=v); c.fill = HEADER_FILL; c.font = WHITE_FONT; c.border = THIN_BORDER
        r+=1
    def data_row(cols, fill=None):
        nonlocal r; _write_row(ws4, r, cols, fill); r+=1
    def blank(): nonlocal r; r+=1

    title("ACC 26年8月新品 — 退货分析结论"); blank()
    section("一、整体退货概况"); header(["指标","数值"])
    data_row(["总销量", f"{s1['总销量']} 件"]); data_row(["总退款数量", f"{s1['总退款数量']} 件"])
    data_row(["总 GMV", f"${s1['总GMV(USD)']:,.2f}"]); data_row(["总退款金额", f"${s1['总退款金额(USD)']:,.2f}"])
    fl = YELLOW_FILL if s1["退件率"] > 10 else None
    data_row(["退件率", f"{s1['退件率']}%"], fl); data_row(["退货率", f"{s1['退货率']}%"]); blank()

    section("二、退货原因分布（按退款数量排序）"); header(["一级原因","退款数量","占比","退款金额","退件率"])
    for it in analysis["section2_reason_dist"]:
        rv = round(it["退款数量"]/it["销量"]*100,2) if it["销量"]>0 else 0
        fl = RED_FILL if it["占比"]>=20 else None
        data_row([r_cn(it["一级原因"]),it["退款数量"],f"{it['占比']}%",f"${it['退款金额']:,.2f}",f"{rv}%"], fl)
    blank()
    section("退货二级原因 TOP 3"); header(["二级原因","退款数量","占比例","退件率"])
    for rn, subs in analysis["section2_sub_reasons"].items():
        for s in subs:
            fl = RED_FILL if s["占比"]>=50 else None
            data_row([s_cn(s["二级原因"]),s["退款数量"],f"{s['占比']}%",""], fl)
    blank()
    tp2 = analysis["section2_reason_dist"][:2]; tp2p = sum(x["占比"] for x in tp2)
    ws4.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    ws4.cell(row=r, column=1, value=f"★ 关键发现：{tp2[0]['一级原因']} + {tp2[1]['一级原因']} 合计占退货的 {tp2p:.1f}%，是核心痛点。").font = Font(bold=True, size=11, color="FF2F5496")
    r+=1; blank()

    section("三、分月退货趋势"); header(["月份","销量","退款数量","退件率","趋势判断"])
    for m in analysis["section3_monthly_trend"]:
        mc = MONTH_CN.get(m["销售月"],m["销售月"]); tg = m.get("标注","")
        if "峰值" in tg: tr="退件率最高月"; fl=RED_FILL
        elif "恶化" in tg: tr="环比恶化"; fl=YELLOW_FILL
        elif "改善" in tg: tr="环比改善"; fl=GREEN_FILL
        else: tr="基准月"; fl=None
        data_row([mc,m["销量"],m["退款数量"],f"{m['退件率']}%",tr], fl)
    blank()
    section("分月退货原因明细"); header(["月份","主要退货原因","退款件数","退件率","备注"])
    for m in analysis["section4_monthly_reason"]:
        mc = MONTH_CN.get(m["销售月"],m["销售月"]); rn = REASON_CN.get(m["一级原因"],""); cn = SUB_CN.get(m["一级原因"],"")
        nm = f"{rn}({cn})" if cn and rn else m["一级原因"]; nt = ""
        if m["退件率"]>50: nt="⚠ 集中爆发"; fl=RED_FILL
        elif m["退件率"]>25: nt="⚠ 需关注"; fl=YELLOW_FILL
        else: fl=None
        data_row([mc,nm,m["退款数量"],f"{m['退件率']}%",nt], fl)
    blank()

    section("四、深层问题诊断")
    for rn, d in analysis["section5_diagnosis"].items():
        cn = REASON_CN.get(rn,rn); subs = [s for s in d.get("二级原因",[]) if s["退款数量"]>0]
        st = ", ".join([f"{s_cn(s['二级原因'])} {s['退款数量']}件({s['占比']}%)" for s in subs])
        ws4.merge_cells(start_row=r, start_column=1, end_row=r+2, end_column=5)
        ws4.cell(row=r, column=1, value=f"【{cn} — 占退货 {d['占总退款比']}%，{d['严重度']}】\n• {st}\n• 涉及 {d['涉及销量']} 件销量，退件率 {d['退件率']}%").alignment = Alignment(wrap_text=True, vertical='top')
        r+=3; blank()

    section("五、改善建议"); header(["优先级","措施","具体方案","预期效果"])
    for pri, ms, pl, ef in [("P0","调整鞋楦/尺码表","与工厂沟通调整鞋楦；商品页增加尺码建议","从根本上解决尺码问题"),
                             ("P0","面料升级/加衬里","增加内衬或使用更厚实的面料","提升质感，减少面料类退货"),
                             ("P1","优化产品图","拍摄实物细节图，展示面料真实质感","管理客户预期"),
                             ("P1","增加试穿反馈","引导客户反馈尺码感受","帮助后续客户选对尺码"),
                             ("P1","周度退货监控","每周追踪退件率变化","及时发现问题趋势")]:
        data_row([pri,ms,pl,ef], RED_FILL if pri=="P0" else YELLOW_FILL)
    blank()

    section("六、改善目标"); header(["维度","现状","目标"])
    tg = analysis["section7_targets"]; ml = analysis["section3_monthly_trend"]
    data_row(["整体退件率",f"{tg['current_rate']}%",f"< {tg['target_rate']}%"])
    data_row(["TOP1原因占比",f"{analysis['section2_reason_dist'][0]['占比']}%","< 20%"])
    data_row(["月度趋势",f"峰值月 → 当前{ml[-1]['退件率']}%","持续改善"]); blank()
    ta = tg.get("top_actions", analysis["section6_suggestions"][:3])
    atxt = "★ 最优先行动项（TOP 3）："
    for i, x in enumerate(ta[:3], 1): atxt += f"\n{i}. [{x.get('优先级','P0')}] {x['原因']} → {x['建议方向']}"
    ws4.merge_cells(start_row=r, start_column=1, end_row=r+1, end_column=5)
    ws4.cell(row=r, column=1, value=atxt).font = Font(bold=True, size=11, color="FF2F5496")
    ws4.column_dimensions['A'].width = 35; ws4.column_dimensions['C'].width = 30

    wb.save(output_path)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python write_excel.py <csv_path> <json_path> <output_path>")
        sys.exit(1)
    out = build_excel(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"Done! → {out}")
