# -*- coding: utf-8 -*-
"""
退货原因分析 — Excel 输出工具
作为模块导入使用：from write_excel import ExcelWriter, write_from_json
也可命令行：python write_excel.py <输入Excel> <分析数据JSON>
"""

import os
import shutil
import json
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# ── 样式常量 ──────────────────────────────────────────
TITLE_FONT   = Font(name="微软雅黑", size=14, bold=True, color="FFFFFF")
TITLE_FILL   = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
HEADER_FONT  = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
HEADER_FILL  = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
SECTION_FONT = Font(name="微软雅黑", size=11, bold=True, color="2F5496")
SECTION_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
NORMAL_FONT  = Font(name="微软雅黑", size=10)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_ALIGN   = Alignment(vertical="center", wrap_text=True)
THIN_BORDER  = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin"),
)
RED_FILL    = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
GREEN_FILL  = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
HIGHLIGHT_MAP = {"red": RED_FILL, "yellow": YELLOW_FILL, "green": GREEN_FILL}


class ExcelWriter:
    """分析结论 Excel 写入器"""

    def __init__(self, filepath, sheet_name="分析结论"):
        base, ext = os.path.splitext(filepath)
        self.output_path = f"{base}_含分析结论{ext}"
        shutil.copy2(filepath, self.output_path)
        self.wb = load_workbook(self.output_path)
        if sheet_name in self.wb.sheetnames:
            del self.wb[sheet_name]
        self.ws = self.wb.create_sheet(sheet_name)
        self.row = 1
        self.cols = 5
        for i, w in enumerate([32, 16, 14, 16, 16], 1):
            self.ws.column_dimensions[get_column_letter(i)].width = w

    def write_title(self, text):
        ws = self.ws
        ws.merge_cells(start_row=self.row, start_column=1, end_row=self.row, end_column=self.cols)
        c = ws.cell(row=self.row, column=1, value=text)
        c.font, c.fill = TITLE_FONT, TITLE_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[self.row].height = 30
        self.row += 1

    def write_section(self, text):
        ws = self.ws
        ws.merge_cells(start_row=self.row, start_column=1, end_row=self.row, end_column=self.cols)
        c = ws.cell(row=self.row, column=1, value=text)
        c.font, c.fill = SECTION_FONT, SECTION_FILL
        c.alignment = Alignment(vertical="center")
        ws.row_dimensions[self.row].height = 24
        self.row += 1

    def write_header(self, headers):
        for i, h in enumerate(headers, 1):
            c = self.ws.cell(row=self.row, column=i, value=h)
            c.font, c.fill, c.alignment, c.border = HEADER_FONT, HEADER_FILL, CENTER_ALIGN, THIN_BORDER
        self.ws.row_dimensions[self.row].height = 22
        self.row += 1

    def write_row(self, values, highlight=None):
        fill = HIGHLIGHT_MAP.get(highlight)
        for i, v in enumerate(values, 1):
            c = self.ws.cell(row=self.row, column=i, value=v)
            c.font = NORMAL_FONT
            c.alignment = CENTER_ALIGN if i > 1 else LEFT_ALIGN
            c.border = THIN_BORDER
            if fill:
                c.fill = fill
        self.row += 1

    def write_text(self, text):
        ws = self.ws
        ws.merge_cells(start_row=self.row, start_column=1, end_row=self.row, end_column=self.cols)
        c = ws.cell(row=self.row, column=1, value=text)
        c.font = NORMAL_FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[self.row].height = max(20, 16 * (text.count("\n") + 1))
        self.row += 1

    def blank(self):
        self.row += 1

    def save(self):
        self.ws.freeze_panes = "A2"
        self.wb.save(self.output_path)
        return self.output_path


def write_from_json(writer, data):
    """
    按 7 大板块写入分析结论。data 结构见 SKILL.md。
    """
    writer.write_title(data["title"])
    writer.blank()

    # 一、整体概况
    writer.write_section("一、整体退货概况")
    writer.write_header(["指标", "数值"])
    for item in data["overview"]:
        writer.write_row([item["指标"], item["数值"]], highlight=item.get("highlight"))
    writer.blank()

    # 二、退货原因分布
    writer.write_section("二、退货原因分布（按退款数量排序）")
    writer.write_header(["一级原因", "退款数量", "占比", "退款金额", "退件率"])
    for item in data["reason_dist"]:
        writer.write_row(
            [item["一级原因"], item["退款数量"], item["占比"], item["退款金额"], item["退件率"]],
            highlight=item.get("highlight"))
    writer.blank()

    writer.write_section("退货二级原因 TOP 3")
    writer.write_header(["二级原因", "退款数量", "占尺码类比例", "退件率", ""])
    for item in data["top3"]:
        writer.write_row(
            [item["二级原因"], item["退款数量"], item["占尺码类比例"], item["退件率"], ""],
            highlight=item.get("highlight"))
    writer.blank()
    writer.write_text(data["key_finding"])
    writer.blank()

    # 三、分月趋势
    writer.write_section("三、分月退货趋势")
    writer.write_header(["月份", "销量", "退款数量", "退件率", "趋势判断"])
    for item in data["monthly_trend"]:
        writer.write_row(
            [item["月份"], item["销量"], item["退款数量"], item["退件率"], item["趋势判断"]],
            highlight=item.get("highlight"))
    writer.blank()

    writer.write_section("分月退货原因明细")
    writer.write_header(["月份", "主要退货原因", "退款件数", "退件率", "备注"])
    for item in data["monthly_detail"]:
        writer.write_row(
            [item["月份"], item["主要退货原因"], item["退款件数"], item["退件率"], item["备注"]],
            highlight=item.get("highlight"))
    writer.blank()

    # 四、深层诊断
    writer.write_section("四、深层问题诊断")
    for text in data["diagnosis"]:
        writer.write_text(text)
        writer.blank()

    # 五、改善建议
    writer.write_section("五、改善建议")
    writer.write_header(["优先级", "措施", "具体方案", "预期效果", ""])
    for item in data["suggestions"]:
        writer.write_row([item["优先级"], item["措施"], item["具体方案"], item["预期效果"], ""])
    writer.blank()

    # 六、改善目标
    writer.write_section("六、改善目标")
    writer.write_header(["维度", "现状", "目标", "", ""])
    for item in data["targets"]:
        writer.write_row([item["维度"], item["现状"], item["目标"], "", ""])
    writer.blank()

    writer.write_text(data["top3_actions"])


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python write_excel.py <输入Excel> <分析数据JSON>")
        sys.exit(1)
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        data = json.load(f)
    w = ExcelWriter(sys.argv[1])
    write_from_json(w, data)
    print(f"Done! 已写入 → {w.save()}")
