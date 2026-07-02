"""
MaxCompute 查询主脚本（终端版本）
读取 SQL 文件 -> 执行查询 -> 输出结果
优化特性：Instance Tunnel 加速、执行耗时监控、LogView 链接显示
"""
import sys
import os
import time
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from odps import ODPS
import pandas as pd
from config import (
    ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_PROJECT, ODPS_ENDPOINT,
    OUTPUT_DIR, OUTPUT_FORMAT
)


def connect_maxcompute():
    """建立 MaxCompute 连接"""
    o = ODPS(ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_PROJECT, endpoint=ODPS_ENDPOINT)
    print(f'[连接成功] 项目: {o.project}')
    return o


def load_sql(sql_file):
    """从 SQL 文件读取查询语句"""
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read().strip()
    # 移除注释和空行
    lines = [line for line in sql.split('\n') if line.strip() and not line.strip().startswith('--')]
    sql = '\n'.join(lines)
    print(f'[加载 SQL] 文件: {sql_file}')
    return sql


def execute_query(o, sql):
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
    return df


def save_result(df, output_file=None):
    """保存查询结果到输出文件"""
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 生成默认文件名
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if OUTPUT_FORMAT == 'excel':
            output_file = os.path.join(OUTPUT_DIR, f'result_{timestamp}.xlsx')
        else:
            output_file = os.path.join(OUTPUT_DIR, f'result_{timestamp}.csv')
    
    # 保存文件
    if output_file.endswith('.xlsx'):
        df.to_excel(output_file, index=False)
    else:
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f'[保存成功] {output_file}')
    return output_file


def main():
    # 默认 SQL 文件路径
    sql_file = os.path.join(os.path.dirname(__file__), 'sql', 'query.sql')
    
    # 支持命令行参数指定 SQL 文件
    if len(sys.argv) > 1:
        sql_file = sys.argv[1]
    
    if not os.path.exists(sql_file):
        print(f'[错误] SQL 文件不存在: {sql_file}')
        sys.exit(1)
    
    # 1. 建立连接
    o = connect_maxcompute()
    
    # 2. 加载 SQL
    sql = load_sql(sql_file)
    
    # 3. 执行查询
    df = execute_query(o, sql)
    
    # 4. 显示结果
    print('\n========== 查询结果 ==========')
    print(df.to_string())
    
    # 5. 保存结果
    output_file = save_result(df)
    print(f'\n完成! 结果已保存到: {output_file}')


if __name__ == '__main__':
    main()
