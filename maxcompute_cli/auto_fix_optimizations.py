#!/usr/bin/env python3
"""
MaxCompute CLI 自动修复脚本
检测缺失的优化项并自动修复
"""
import sys
import os
import re

def read_file(filepath):
    """读取文件内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filepath, content):
    """写入文件内容"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def check_and_fix_main_py(main_py):
    """检查并修复 main.py"""
    content = read_file(main_py)
    fixed = False
    
    # 1. 检查是否导入 time 模块
    if 'import time' not in content:
        print("[FIX] 添加 import time")
        content = re.sub(
            r'(import sys\nimport os)',
            r'\1\nimport time',
            content
        )
        fixed = True
    
    # 2. 检查 execute_query 函数是否包含优化代码
    if 'tunnel=True' not in content:
        print("[FIX] 添加 Instance Tunnel 加速")
        # 替换旧的 execute_query 函数
        old_pattern = r'def execute_query\(o, sql\):.*?return df'
        new_func = '''def execute_query(o, sql):
    """执行 SQL 查询（优化版：Instance Tunnel 加速 + 耗时监控）"""
    print(f'[执行查询] {sql[:100]}...' if len(sql) > 100 else f'[执行查询] {sql}')
    
    # 开始计时
    start_time = time.time()
    
    # 执行 SQL 并获取 instance
    instance = o.execute_sql(sql)
    
    # 显示 Instance ID 和 LogView 链接
    print(f'  Instance ID: {instance.id}')
    print(f'  LogView: {instance.get_logview_address()}')
    
    # 等待执行完成
    instance.wait_for_success()
    
    exec_time = time.time() - start_time
    print(f'✓ SQL 执行耗时: {exec_time:.1f}秒')
    
    # 读取结果（使用 tunnel=True 加速数据传输）
    print('正在下载结果...')
    download_start = time.time()
    
    with instance.open_reader(tunnel=True) as reader:
        df = reader.to_pandas()
    
    download_time = time.time() - download_start
    total_time = time.time() - start_time
    
    print(f'✓ 下载耗时: {download_time:.1f}秒')
    print(f'✓ 总耗时: {total_time:.1f}秒')
    print(f'✓ 查询完成: {len(df)} 行, {len(df.columns)} 列')
    return df'''
        
        content = re.sub(old_pattern, new_func, content, flags=re.DOTALL)
        fixed = True
    
    # 3. 更新 docstring
    if '优化特性' not in content.split('\n')[0:5]:
        print("[FIX] 更新文档字符串")
        content = re.sub(
            r'MaxCompute 查询主脚本（终端版本）\n读取 SQL 文件 -> 执行查询 -> 输出结果',
            'MaxCompute 查询主脚本（终端版本）\n读取 SQL 文件 -> 执行查询 -> 输出结果\n优化特性：Instance Tunnel 加速、执行耗时监控、LogView 链接显示',
            content
        )
        fixed = True
    
    if fixed:
        write_file(main_py, content)
        print("[SUCCESS] main.py 已修复\n")
        return True
    else:
        print("[OK] main.py 无需修复\n")
        return False

def check_and_fix_config_py(config_py):
    """检查并修复 config.py"""
    content = read_file(config_py)
    fixed = False
    
    # 检查超时时间是否为 300
    if 'SQL_TIMEOUT = 120' in content:
        print("[FIX] 更新 SQL_TIMEOUT 为 300 秒")
        content = content.replace('SQL_TIMEOUT = 120', 'SQL_TIMEOUT = 300')
        fixed = True
    
    if fixed:
        write_file(config_py, content)
        print("[SUCCESS] config.py 已修复\n")
        return True
    else:
        print("[OK] config.py 无需修复\n")
        return False

def main():
    print("=" * 60)
    print("MaxCompute CLI 自动修复工具")
    print("=" * 60)
    print()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, 'main.py')
    config_py = os.path.join(base_dir, 'config.py')
    
    any_fixed = False
    
    # 检查并修复 main.py
    print("【检查 main.py】")
    print("-" * 60)
    any_fixed |= check_and_fix_main_py(main_py)
    
    # 检查并修复 config.py
    print("【检查 config.py】")
    print("-" * 60)
    any_fixed |= check_and_fix_config_py(config_py)
    
    # 总结
    print("=" * 60)
    if any_fixed:
        print("[DONE] 修复完成！请运行 verify_all_optimizations.py 验证")
    else:
        print("[OK] 所有文件已是最新优化版本")
    print("=" * 60)

if __name__ == '__main__':
    main()
