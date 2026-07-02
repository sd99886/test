#!/usr/bin/env python3
"""
MaxCompute CLI 优化验证脚本
自动检查所有性能优化是否已正确应用
"""
import sys
import os

def check_file_exists(filepath):
    """检查文件是否存在"""
    if not os.path.exists(filepath):
        print(f"[FAIL] 文件不存在: {filepath}")
        return False
    return True

def check_content(filepath, keyword, description):
    """检查文件中是否包含指定内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if keyword in content:
                print(f"[OK] {description}")
                return True
            else:
                print(f"[FAIL] {description} - 未找到关键字: {keyword}")
                return False
    except Exception as e:
        print(f"[ERROR] 读取文件失败: {e}")
        return False

def main():
    print("=" * 60)
    print("MaxCompute CLI 优化验证")
    print("=" * 60)
    print()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, 'main.py')
    config_py = os.path.join(base_dir, 'config.py')
    
    all_passed = True
    
    # 1. 检查文件存在性
    print("【1】文件存在性检查")
    print("-" * 60)
    all_passed &= check_file_exists(main_py)
    all_passed &= check_file_exists(config_py)
    print()
    
    # 2. 检查 main.py 优化项
    print("【2】main.py 优化项检查")
    print("-" * 60)
    all_passed &= check_content(main_py, 'import time', '导入 time 模块')
    all_passed &= check_content(main_py, 'tunnel=True', 'Instance Tunnel 加速 (tunnel=True)')
    all_passed &= check_content(main_py, 'time.time()', '耗时监控 (time.time())')
    all_passed &= check_content(main_py, 'wait_for_success()', '等待执行完成 (wait_for_success)')
    all_passed &= check_content(main_py, 'LogView', 'LogView 链接显示')
    all_passed &= check_content(main_py, 'instance.id', 'Instance ID 显示')
    all_passed &= check_content(main_py, 'download_time', '下载耗时统计')
    all_passed &= check_content(main_py, 'total_time', '总耗时统计')
    print()
    
    # 3. 检查 config.py 配置
    print("【3】config.py 配置检查")
    print("-" * 60)
    all_passed &= check_content(config_py, 'SQL_TIMEOUT = 300', '超时时间调整为 300 秒')
    all_passed &= check_content(config_py, 'ODPS_ACCESS_ID', 'AccessKey ID 配置')
    all_passed &= check_content(config_py, 'cupshe_bigdata_ads', 'Project 配置')
    print()
    
    # 4. 总结
    print("=" * 60)
    if all_passed:
        print("[SUCCESS] 所有优化项验证通过！")
        print()
        print("下一步操作：")
        print("  1. 运行测试: python main.py")
        print("  2. 观察输出中的耗时信息")
        print("  3. 点击 LogView 链接查看详细执行计划")
        return 0
    else:
        print("[ERROR] 部分优化项验证失败，请检查上述 [FAIL] 项")
        return 1

if __name__ == '__main__':
    sys.exit(main())
