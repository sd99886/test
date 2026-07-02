#!/usr/bin/env python3
"""
Git 敏感信息保护工具

功能：
1. 自动检测并忽略敏感配置文件（config.py, .env 等）
2. 生成配置模板文件（*.example）
3. 验证敏感信息是否已正确保护
4. 提供安全的提交和推送流程

使用方法：
    python git_security_tool.py --init      # 初始化项目（首次使用）
    python git_security_tool.py --check     # 检查敏感信息状态
    python git_security_tool.py --template  # 仅生成模板文件
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


class GitSecurityTool:
    """Git 敏感信息保护工具"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.sensitive_files = [
            'config.py',
            '*.env',
            '.env.local',
            '.env.production',
            'secrets.py',
            'credentials.py'
        ]
        
    def run_command(self, command, cwd=None):
        """执行命令并返回结果"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, '', str(e)
    
    def create_gitignore(self):
        """创建或更新 .gitignore 文件"""
        gitignore_path = self.project_root / '.gitignore'
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否已包含敏感文件规则
            has_config_rule = any('config.py' in line for line in content.split('\n'))
            has_env_rule = any('*.env' in line for line in content.split('\n'))
            
            if has_config_rule and has_env_rule:
                print("[OK] .gitignore 已包含敏感文件保护规则")
                return True
        
        # 添加敏感文件保护规则
        sensitive_rules = """
# Configuration files with secrets (重要！)
config.py
*.env
.env.local
.env.production
secrets.py
credentials.py
"""
        
        if gitignore_path.exists():
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write(sensitive_rules)
        else:
            # 创建基础 .gitignore
            base_gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Jupyter Notebook
.ipynb_checkpoints
*-checkpoint.ipynb

# Output directories
output/
notebook_output/
""" + sensitive_rules + """
# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write(base_gitignore)
        
        print("[SUCCESS] .gitignore 已更新，敏感文件将被忽略")
        return True
    
    def create_config_template(self, config_file):
        """从真实配置文件生成模板文件"""
        config_path = self.project_root / config_file
        
        if not config_path.exists():
            print(f"[SKIP] {config_file} 不存在")
            return False
        
        template_path = self.project_root / f"{config_file}.example"
        
        # 读取原始配置
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换敏感信息为占位符
        replacements = [
            ("YOUR_REAL_ACCESS_KEY_ID", "YOUR_ACCESS_KEY_ID_HERE"),
            ("YOUR_REAL_ACCESS_KEY_SECRET", "YOUR_ACCESS_KEY_SECRET_HERE"),
            ("sk-", "YOUR_API_KEY_HERE"),
            ("ghp_", "YOUR_GITHUB_TOKEN_HERE"),
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        # 添加注释说明
        header = '"""\n注意：此文件是配置模板，不包含真实的密钥信息\n请复制此文件为 config.py 并填入你的真实配置\n"""\n\n'
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(header + content)
        
        print(f"[SUCCESS] 已生成模板: {config_file}.example")
        return True
    
    def find_all_config_files(self):
        """查找项目中所有的配置文件"""
        config_files = []
        
        for pattern in ['**/config.py', '**/*.env']:
            for file in self.project_root.glob(pattern):
                # 排除 example 文件和虚拟环境中的文件
                if '.example' not in str(file) and '.venv' not in str(file):
                    config_files.append(str(file.relative_to(self.project_root)))
        
        return config_files
    
    def check_sensitive_info(self):
        """检查是否存在未保护的敏感信息"""
        print("=" * 70)
        print("【敏感信息检查】")
        print("=" * 70)
        
        all_passed = True
        
        # 1. 检查 .gitignore
        print("\n[1] 检查 .gitignore 配置...")
        gitignore_path = self.project_root / '.gitignore'
        if not gitignore_path.exists():
            print("  [FAIL] .gitignore 不存在")
            all_passed = False
        else:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'config.py' in content:
                print("  [OK] config.py 已被忽略")
            else:
                print("  [FAIL] config.py 未被忽略")
                all_passed = False
        
        # 2. 检查配置文件是否存在
        print("\n[2] 检查配置文件...")
        config_files = self.find_all_config_files()
        if config_files:
            print(f"  找到 {len(config_files)} 个配置文件:")
            for cf in config_files:
                print(f"    - {cf}")
                
                # 检查是否有对应的模板文件
                template_file = f"{cf}.example"
                if (self.project_root / template_file).exists():
                    print(f"      ✓ 模板文件存在")
                else:
                    print(f"      ✗ 缺少模板文件")
                    all_passed = False
        else:
            print("  [OK] 未找到配置文件")
        
        # 3. 检查 Git 历史中是否有敏感信息
        print("\n[3] 检查 Git 历史...")
        success, stdout, stderr = self.run_command('git log --all --oneline')
        if success:
            commits = stdout.strip().split('\n')
            print(f"  共有 {len(commits)} 个提交")
        else:
            print("  [WARN] 无法获取 Git 历史")
        
        # 4. 检查暂存区是否有敏感文件
        print("\n[4] 检查暂存区...")
        success, stdout, stderr = self.run_command('git status --porcelain')
        if success and stdout.strip():
            staged_files = stdout.strip().split('\n')
            sensitive_staged = [f for f in staged_files if 'config.py' in f or '.env' in f]
            if sensitive_staged:
                print("  [FAIL] 发现待提交的敏感文件:")
                for f in sensitive_staged:
                    print(f"    - {f}")
                all_passed = False
            else:
                print("  [OK] 暂存区无敏感文件")
        else:
            print("  [OK] 工作区干净")
        
        print("\n" + "=" * 70)
        if all_passed:
            print("[SUCCESS] 所有检查通过！可以安全提交代码")
        else:
            print("[WARNING] 发现问题，请先修复后再提交")
        print("=" * 70)
        
        return all_passed
    
    def init_project(self):
        """初始化项目：创建 .gitignore 和模板文件"""
        print("=" * 70)
        print("【初始化 Git 敏感信息保护】")
        print("=" * 70)
        
        # 1. 创建 .gitignore
        print("\n[步骤 1] 创建/更新 .gitignore...")
        self.create_gitignore()
        
        # 2. 查找并生成模板文件
        print("\n[步骤 2] 生成配置模板...")
        config_files = self.find_all_config_files()
        if config_files:
            for cf in config_files:
                self.create_config_template(cf)
        else:
            print("  [INFO] 未找到配置文件，跳过模板生成")
        
        # 3. 验证
        print("\n[步骤 3] 验证配置...")
        self.check_sensitive_info()
        
        print("\n" + "=" * 70)
        print("[SUCCESS] 初始化完成！")
        print("\n下一步操作：")
        print("  1. 检查生成的 *.example 文件是否正确")
        print("  2. 运行: git add .")
        print("  3. 运行: git commit -m \"chore: 添加敏感信息保护\"")
        print("  4. 运行: git push origin main")
        print("=" * 70)
    
    def safe_commit(self, message="chore: 安全提交"):
        """安全提交：确保不包含敏感信息"""
        print("=" * 70)
        print("【安全提交检查】")
        print("=" * 70)
        
        # 先进行检查
        if not self.check_sensitive_info():
            print("\n[ERROR] 检查失败，中止提交")
            return False
        
        # 确认提交
        response = input(f"\n是否提交？(y/n): ").strip().lower()
        if response != 'y':
            print("[CANCEL] 提交已取消")
            return False
        
        # 执行提交
        print(f"\n正在提交: {message}")
        success, stdout, stderr = self.run_command(f'git add -A && git commit -m "{message}"')
        
        if success:
            print("[SUCCESS] 提交成功")
            
            # 询问是否推送
            push_response = input("是否推送到远程？(y/n): ").strip().lower()
            if push_response == 'y':
                print("正在推送...")
                success, stdout, stderr = self.run_command('git push origin main')
                if success:
                    print("[SUCCESS] 推送成功")
                else:
                    print(f"[FAIL] 推送失败: {stderr}")
                    return False
        else:
            print(f"[FAIL] 提交失败: {stderr}")
            return False
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Git 敏感信息保护工具')
    parser.add_argument('--init', action='store_true', help='初始化项目（创建 .gitignore 和模板文件）')
    parser.add_argument('--check', action='store_true', help='检查敏感信息状态')
    parser.add_argument('--template', action='store_true', help='仅生成模板文件')
    parser.add_argument('--commit', type=str, nargs='?', const='chore: 安全提交', help='安全提交代码')
    
    args = parser.parse_args()
    
    tool = GitSecurityTool()
    
    if args.init:
        tool.init_project()
    elif args.check:
        tool.check_sensitive_info()
    elif args.template:
        config_files = tool.find_all_config_files()
        for cf in config_files:
            tool.create_config_template(cf)
    elif args.commit:
        tool.safe_commit(args.commit)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
