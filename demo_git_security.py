#!/usr/bin/env python3
"""
Git 敏感信息保护 - 快速演示脚本

此脚本演示如何安全地管理包含敏感信息的 Git 项目。
运行此脚本将自动执行完整的保护流程。
"""

import os
import sys
from pathlib import Path


def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(f"【{title}】")
    print("=" * 70)


def print_step(step_num, description):
    """打印步骤"""
    print(f"\n[步骤 {step_num}] {description}")
    print("-" * 70)


def main():
    project_root = Path(__file__).parent.absolute()
    
    print_section("Git 敏感信息保护 - 完整演示")
    
    print("""
本演示将展示如何：
1. 创建 .gitignore 文件保护敏感配置
2. 生成配置模板文件（不含真实密钥）
3. 验证配置是否正确
4. 安全提交代码到 Git

注意：此脚本不会修改你本地的 config.py 文件，
      你的真实配置仍然可以正常使用！
""")
    
    input("\n按 Enter 开始演示...")
    
    # 步骤 1: 检查当前状态
    print_step(1, "检查当前项目状态")
    print("正在扫描项目中的配置文件...")
    
    config_files = []
    for pattern in ['**/config.py', '**/*.env']:
        for file in project_root.glob(pattern):
            if '.example' not in str(file) and '.venv' not in str(file):
                config_files.append(str(file.relative_to(project_root)))
    
    if config_files:
        print(f"\n发现 {len(config_files)} 个配置文件:")
        for cf in config_files:
            print(f"  ✓ {cf}")
            
            # 检查是否有模板文件
            template_file = f"{cf}.example"
            if (project_root / template_file).exists():
                print(f"    → 已有模板: {template_file}")
            else:
                print(f"     缺少模板文件")
    else:
        print("\n未发现配置文件")
    
    input("\n按 Enter 继续...")
    
    # 步骤 2: 检查 .gitignore
    print_step(2, "检查 .gitignore 配置")
    
    gitignore_path = project_root / '.gitignore'
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'config.py' in content:
            print("\n✓ .gitignore 已正确配置，config.py 将被忽略")
        else:
            print("\n✗ .gitignore 未包含 config.py 规则")
            print("建议添加以下行到 .gitignore:")
            print("  config.py")
            print("  *.env")
    else:
        print("\n✗ .gitignore 不存在")
        print("需要创建 .gitignore 文件")
    
    input("\n按 Enter 继续...")
    
    # 步骤 3: 演示配置文件的分离
    print_step(3, "配置文件分离策略")
    
    print("""
┌─────────────────────────────────────────────────┐
│              配置文件管理策略                      │
├─────────────────────────────────────────────────┤
│                                                   │
│  📁 本地文件 (不提交到 Git):                       │
│     • config.py          ← 包含真实 AccessKey     │
│     • .env               ← 环境变量配置           │
│     • secrets.py         ← 其他敏感信息           │
│                                                   │
│  📁 Git 仓库 (安全提交):                          │
│     • config.py.example  ← 配置模板（无真实密钥）  │
│     • .env.example       ← 环境变量模板           │
│     • .gitignore         ← 忽略规则               │
│     • main.py            ← 业务代码               │
│     • query.ipynb        ← Jupyter Notebook       │
│                                                   │
└─────────────────────────────────────────────────┘

工作原理:
1. 开发者在本地创建 config.py，填入真实密钥
2. .gitignore 确保 config.py 不会被 git add 添加
3. 提交时只包含 config.py.example（模板文件）
4. 团队成员克隆后，复制模板并填入自己的密钥
""")
    
    input("\n按 Enter 继续...")
    
    # 步骤 4: 演示安全提交流程
    print_step(4, "安全提交流程演示")
    
    print("""
正确的提交流程:

1️  修改代码后，检查状态
   $ git status
   
   输出示例:
   On branch main
   Changes to be committed:
     modified:   main.py
     new file:   feature.py
   
   注意: config.py 不应该出现在列表中！

2️⃣  验证敏感文件被正确忽略
   $ git check-ignore config.py
   
   输出: .gitignore:35:config.py  config.py
   （有输出说明已被忽略）

3️⃣  添加并提交
   $ git add -A
   $ git commit -m "feat: 添加新功能"

4️⃣  推送到远程
   $ git push origin main

❌ 错误做法:
   $ git add config.py  # 不要强制添加被忽略的文件！
   $ git add -f config.py  # 绝对不要这样做！
""")
    
    input("\n按 Enter 继续...")
    
    # 步骤 5: 常见问题处理
    print_step(5, "常见问题处理")
    
    print("""
问题 1: GitHub 阻止推送，提示包含密钥
─────────────────────────────────────
原因: Git 历史中曾包含敏感信息

解决方案:
A. 重写 Git 历史（推荐）
   $ git checkout -b clean-main <clean-commit-hash>
   $ git checkout main -- .
   $ git push origin clean-main --force

B. 使用 BFG Repo-Cleaner
   $ java -jar bfg.jar --replace-text passwords.txt my-repo.git

C. 在 GitHub 上允许密钥（仅测试环境）
   访问 GitHub 提供的 unblock-secret 链接


问题 2: config.py 意外被提交
─────────────────────────────────────
立即处理:
$ git reset HEAD~1          # 撤销提交
$ echo "config.py" >> .gitignore  # 添加到忽略列表
$ git add .gitignore
$ git commit -m "chore: 修复敏感信息泄露"


问题 3: 团队成员不知道如何配置
─────────────────────────────────────
提供清晰的 README 说明:

## 快速开始

1. 克隆仓库
   $ git clone https://github.com/xxx/repo.git

2. 复制配置模板
   $ cp config.py.example config.py

3. 编辑 config.py，填入你的 AccessKey

4. 开始开发
   $ python main.py
""")
    
    input("\n按 Enter 继续...")
    
    # 步骤 6: 自动化脚本介绍
    print_step(6, "自动化脚本工具")
    
    print("""
我们提供了自动化脚本简化整个流程:

📦 git_security_tool.py

可用命令:

1. 初始化项目（首次使用）
   $ python git_security_tool.py --init
   
   功能:
   • 创建/更新 .gitignore
   • 生成所有配置模板
   • 验证配置正确性

2. 检查敏感信息状态
   $ python git_security_tool.py --check
   
   功能:
   • 检查 .gitignore 配置
   • 检查配置文件和模板
   • 检查暂存区是否有敏感文件
   • 给出通过/失败报告

3. 仅生成模板文件
   $ python git_security_tool.py --template

4. 安全提交代码
   $ python git_security_tool.py --commit "提交信息"
   
   功能:
   • 先执行敏感信息检查
   • 确认后提交代码
   • 可选推送到远程

 最佳实践:
• 每次提交前运行 --check
• 新项目先运行 --init
• 定期审查 .gitignore 配置
""")
    
    input("\n按 Enter 查看总结...")
    
    # 总结
    print_section("总结")
    
    print("""
✅ 你现在已经了解:

1. 为什么要保护敏感信息
   • 防止密钥泄露
   • 避免 GitHub 阻止推送
   • 保护项目安全

2. 如何保护敏感信息
   • 使用 .gitignore 忽略敏感文件
   • 提供配置模板供团队使用
   • 定期检查和验证

3. 如何处理已泄露的密钥
   • 重写 Git 历史
   • 使用 BFG 清理工具
   • 更换新的 AccessKey

4. 如何使用自动化工具
   • git_security_tool.py --init
   • git_security_tool.py --check
   • git_security_tool.py --commit

📚 详细文档: GIT_SECURITY_GUIDE.md

 下一步:
   1. 运行: python git_security_tool.py --check
   2. 确认所有检查通过
   3. 安全提交你的代码

如有问题，请参考 GIT_SECURITY_GUIDE.md 或联系技术支持。
""")
    
    print("\n" + "=" * 70)
    print("演示结束！感谢观看 🎉")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n演示已取消")
        sys.exit(0)
