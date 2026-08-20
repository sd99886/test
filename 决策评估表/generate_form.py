import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "离职决策评估表"

# Styles
title_font = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
title_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
dim_font = Font(name="微软雅黑", size=11, bold=True, color="2F5496")
dim_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
normal_font = Font(name="微软雅黑", size=10)
score_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
result_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
thin_border = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin")
)
center = Alignment(horizontal="center", vertical="center", wrap_text=True)
left_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

# Column widths
ws.column_dimensions["A"].width = 6
ws.column_dimensions["B"].width = 14
ws.column_dimensions["C"].width = 50
ws.column_dimensions["D"].width = 12
ws.column_dimensions["E"].width = 30

# Title
ws.merge_cells("A1:E1")
ws["A1"] = "离职决策评估表"
ws["A1"].font = title_font
ws["A1"].fill = title_fill
ws["A1"].alignment = center
ws.row_dimensions[1].height = 36

# Instructions
ws.merge_cells("A2:E2")
ws["A2"] = "填写说明：每题按实际情况打 1-5 分（1=完全不符合/情况很好，5=完全符合/情况很差），填完 D 列分数后自动计算总分。"
ws["A2"].font = Font(name="微软雅黑", size=9, italic=True, color="666666")
ws["A2"].alignment = left_wrap
ws.row_dimensions[2].height = 30

# Headers
headers = ["题号", "评估维度", "评估题目", "你的评分(1-5)", "评分参考标准"]
for col, h in enumerate(headers, 1):
    cell = ws.cell(row=3, column=col, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border
ws.row_dimensions[3].height = 28

# Questions data: (dimension, weight, question, standard)
questions = [
    ("健康与情绪", 0.25, "工作对我的睡眠或身体健康造成了明显负面影响", "1=毫无影响  3=偶尔影响  5=严重失眠/躯体化"),
    ("健康与情绪", 0.25, "我长期处于焦虑、压抑或抑郁的情绪状态", "1=情绪稳定  3=时常焦虑  5=长期情绪低落"),
    ("健康与情绪", 0.25, "周末或下班后我无法真正放松，总被工作牵动", "1=完全能放松  3=偶尔想到工作  5=时刻紧绷"),
    ("成长与发展", 0.25, "我在当前岗位已经学不到新东西，工作全是重复", "1=持续成长  3=成长放缓  5=完全停滞"),
    ("成长与发展", 0.25, "内部晋升或转岗到目标方向的机会基本无望", "1=机会明确  3=不确定  5=完全无望"),
    ("成长与发展", 0.25, "我的技能在就业市场上的竞争力正在贬值", "1=在提升  3=持平  5=明显落后市场"),
    ("回报与公平", 0.20, "我的薪资明显低于市场同岗位水平", "1=高于市场  3=基本持平  5=明显偏低"),
    ("回报与公平", 0.20, "我的付出和回报（薪资/晋升/认可）严重不匹配", "1=匹配  3=略有差距  5=严重不匹配"),
    ("回报与公平", 0.20, "公司的绩效评价或晋升机制让我感到不公平", "1=公平透明  3=有瑕疵  5=严重不公"),
    ("公司与团队", 0.15, "公司业务前景不明，持续收缩或频繁动荡", "1=向好发展  3=有不确定性  5=持续恶化"),
    ("公司与团队", 0.15, "团队核心人员批量流失，稳定性很差", "1=稳定  3=有人离开  5=批量流失"),
    ("公司与团队", 0.15, "我和直接领导的关系让我长期内耗", "1=关系良好  3=一般  5=严重内耗"),
    ("价值观与意义", 0.15, "公司的某些做法触及了我的价值观底线", "1=完全没有  3=偶尔不适  5=经常触及"),
    ("价值观与意义", 0.15, "我觉得当前的工作内容毫无意义感", "1=很有意义  3=意义一般  5=毫无意义"),
]

row = 4
dimensions = {}
for i, (dim, weight, q, std) in enumerate(questions, 1):
    ws.cell(row=row, column=1, value=i).font = normal_font
    ws.cell(row=row, column=1).alignment = center
    ws.cell(row=row, column=1).border = thin_border

    ws.cell(row=row, column=2, value=dim).font = dim_font
    ws.cell(row=row, column=2).fill = dim_fill
    ws.cell(row=row, column=2).alignment = center
    ws.cell(row=row, column=2).border = thin_border

    ws.cell(row=row, column=3, value=q).font = normal_font
    ws.cell(row=row, column=3).alignment = left_wrap
    ws.cell(row=row, column=3).border = thin_border

    score_cell = ws.cell(row=row, column=4)
    score_cell.fill = score_fill
    score_cell.alignment = center
    score_cell.border = thin_border
    score_cell.font = Font(name="微软雅黑", size=11, bold=True, color="C00000")

    ws.cell(row=row, column=5, value=std).font = Font(name="微软雅黑", size=9, color="666666")
    ws.cell(row=row, column=5).alignment = left_wrap
    ws.cell(row=row, column=5).border = thin_border

    ws.row_dimensions[row].height = 32
    dimensions.setdefault(dim, []).append(row)
    row += 1

# Dimension subtotals
row += 1
ws.merge_cells(f"A{row}:E{row}")
ws.cell(row=row, column=1, value="—— 各维度得分（自动计算）——").font = Font(name="微软雅黑", size=11, bold=True, color="2F5496")
ws.cell(row=row, column=1).alignment = center
ws.cell(row=row, column=1).fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
row += 1

dim_headers = ["维度", "权重", "平均分(1-5)", "加权得分", "维度评价"]
for col, h in enumerate(dim_headers, 1):
    cell = ws.cell(row=row, column=col, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border
row += 1

dim_summary_start = row
dim_info = [
    ("健康与情绪", 0.25),
    ("成长与发展", 0.25),
    ("回报与公平", 0.20),
    ("公司与团队", 0.15),
    ("价值观与意义", 0.15),
]
for dim_name, weight in dim_info:
    rows_in_dim = dimensions[dim_name]
    avg_formula = f"=AVERAGE(D{rows_in_dim[0]}:D{rows_in_dim[-1]})"
    weighted_formula = f"=C{row}*{weight}*20"  # convert 1-5 to 0-100 then weight

    ws.cell(row=row, column=1, value=dim_name).font = dim_font
    ws.cell(row=row, column=1).fill = dim_fill
    ws.cell(row=row, column=1).alignment = center
    ws.cell(row=row, column=1).border = thin_border

    ws.cell(row=row, column=2, value=f"{int(weight*100)}%").font = normal_font
    ws.cell(row=row, column=2).alignment = center
    ws.cell(row=row, column=2).border = thin_border

    ws.cell(row=row, column=3, value=avg_formula).font = normal_font
    ws.cell(row=row, column=3).alignment = center
    ws.cell(row=row, column=3).border = thin_border
    ws.cell(row=row, column=3).number_format = "0.00"

    ws.cell(row=row, column=4, value=weighted_formula).font = Font(name="微软雅黑", size=10, bold=True)
    ws.cell(row=row, column=4).alignment = center
    ws.cell(row=row, column=4).border = thin_border
    ws.cell(row=row, column=4).number_format = "0.0"

    eval_formula = f'=IF(C{row}="","待填写",IF(C{row}<=2,"状态良好",IF(C{row}<=3,"轻度不满",IF(C{row}<=4,"中度问题","严重预警"))))'
    ws.cell(row=row, column=5, value=eval_formula).font = normal_font
    ws.cell(row=row, column=5).alignment = center
    ws.cell(row=row, column=5).border = thin_border

    row += 1

# Total score
row += 1
ws.merge_cells(f"A{row}:B{row}")
ws.cell(row=row, column=1, value="综合得分（满分100）").font = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")
ws.cell(row=row, column=1).fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
ws.cell(row=row, column=1).alignment = center
ws.cell(row=row, column=1).border = thin_border

total_formula = f"=SUM(D{dim_summary_start}:D{dim_summary_start+4})"
ws.cell(row=row, column=3, value=total_formula).font = Font(name="微软雅黑", size=14, bold=True, color="C00000")
ws.cell(row=row, column=3).fill = result_fill
ws.cell(row=row, column=3).alignment = center
ws.cell(row=row, column=3).border = thin_border
ws.cell(row=row, column=3).number_format = "0.0"

ws.merge_cells(f"D{row}:E{row}")
verdict_formula = f'=IF(C{row}="","请先填写评分",IF(C{row}<=40,"暂不建议离职，当前状态尚可",IF(C{row}<=60,"有不满但可观察，先尝试内部解决",IF(C{row}<=80,"建议开始看机会，做好离职准备","建议尽快离职，当前环境伤害大于收益"))))'
ws.cell(row=row, column=4, value=verdict_formula).font = Font(name="微软雅黑", size=11, bold=True, color="2F5496")
ws.cell(row=row, column=4).fill = result_fill
ws.cell(row=row, column=4).alignment = center
ws.cell(row=row, column=4).border = thin_border
ws.row_dimensions[row].height = 36

# Score interpretation guide
row += 2
ws.merge_cells(f"A{row}:E{row}")
ws.cell(row=row, column=1, value="评分区间解读").font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
ws.cell(row=row, column=1).fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
ws.cell(row=row, column=1).alignment = center
row += 1

intervals = [
    ("0 - 40 分", "暂不建议离职", "当前工作整体可接受，问题是局部的、可解决的"),
    ("41 - 60 分", "观察期", "有不满情绪，但尚未到必须走的程度，先尝试内部沟通、换组、调整心态"),
    ("61 - 80 分", "准备期", "多个维度出现明显问题，建议开始更新简历、看机会、存缓冲金"),
    ("81 - 100 分", "行动期", "当前环境对你的伤害已大于收益，建议尽快推进离职，优先考虑健康"),
]
for score_range, verdict, advice in intervals:
    ws.cell(row=row, column=1, value=score_range).font = Font(name="微软雅黑", size=10, bold=True)
    ws.cell(row=row, column=1).alignment = center
    ws.cell(row=row, column=1).border = thin_border
    ws.merge_cells(f"B{row}:C{row}")
    ws.cell(row=row, column=2, value=verdict).font = Font(name="微软雅黑", size=10, bold=True, color="C00000")
    ws.cell(row=row, column=2).alignment = center
    ws.cell(row=row, column=2).border = thin_border
    ws.merge_cells(f"D{row}:E{row}")
    ws.cell(row=row, column=4, value=advice).font = Font(name="微软雅黑", size=9)
    ws.cell(row=row, column=4).alignment = left_wrap
    ws.cell(row=row, column=4).border = thin_border
    ws.row_dimensions[row].height = 28
    row += 1

# Freeze panes
ws.freeze_panes = "A4"

output_path = r"C:\Users\Cupshe\Doubao\chats\2026-08-17\new-chat\离职决策评估表.xlsx"
wb.save(output_path)
print(f"Saved to {output_path}")
