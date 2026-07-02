import json

# 读取 notebook 文件
with open('query.ipynb', 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# 找到并删除 SQL 编写区的两个 cell（markdown + code）
cells_to_keep = []
for cell in notebook['cells']:
    # 跳过 SQL 编写区的 markdown cell
    if cell.get('cell_type') == 'markdown' and 'SQL 编写区' in ''.join(cell.get('source', [])):
        print(f"删除 SQL 编写区 markdown cell")
        continue
    # 跳过 SQL 编写区的 code cell
    if cell.get('id') == 'write_sql':
        print(f"删除 SQL 编写区 code cell")
        continue
    cells_to_keep.append(cell)

notebook['cells'] = cells_to_keep

# 修改连接 cell，添加读取 SQL 文件的代码
for cell in notebook['cells']:
    if cell.get('id') == 'connect' and cell.get('cell_type') == 'code':
        source = cell['source']
        # 如果 source 是列表，转换为字符串处理
        if isinstance(source, list):
            source_text = ''.join(source)
        else:
            source_text = source
        
        # 添加读取 SQL 的代码
        sql_reading_code = '''
# 从外部 SQL 文件读取查询语句
sql_file = 'sql/query.sql'
with open(sql_file, 'r', encoding='utf-8') as f:
    sql = f.read().strip()
print(f'✓ 已从 {sql_file} 加载 SQL 查询脚本')'''
        
        # 将新代码添加到末尾
        if isinstance(source, list):
            source.append('\n')
            for line in sql_reading_code.split('\n'):
                source.append(line + '\n')
        else:
            cell['source'] = source_text + sql_reading_code
        
        print(f"已添加 SQL 文件读取代码到连接 cell")
        break

# 保存修改后的 notebook
with open('query.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print("✅ Notebook 修改完成！")
