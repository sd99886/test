# Git 敏感信息保护工具包

##  概述

本文件夹包含完整的 Git 敏感信息保护工具和文档，用于防止 AccessKey、API Key 等敏感信息泄露到 Git 仓库。

---

##  快速开始

### 1. 查看主文档

首先阅读 [README.md](README.md) 了解整体方案。

### 2. 运行演示（可选）

```bash
python demo_git_security.py
```

交互式教程，展示完整的使用流程。

### 3. 初始化项目

```bash
python git_security_tool.py --init
```

自动创建 `.gitignore` 和配置模板文件。

### 4. 检查状态

```bash
python git_security_tool.py --check
```

验证敏感信息是否已正确保护。

### 5. 安全提交

```bash
python git_security_tool.py --commit "feat: 你的修改"
```

或直接使用 Git 命令：

```bash
git add -A
git commit -m "feat: 你的修改"
git push origin main
```

---

## 📁 文件说明

### 工具脚本

| 文件 | 说明 |
|------|------|
| [git_security_tool.py](git_security_tool.py) | **核心自动化脚本**<br/>• `--init`：初始化项目<br/>• `--check`：检查状态<br/>• `--template`：生成模板<br/>• `--commit`：安全提交 |
| [demo_git_security.py](demo_git_security.py) | **交互式演示脚本**<br/>6 步骤完整教程，适合新成员学习 |

### 文档

| 文件 | 说明 | 适用场景 |
|------|------|----------|
| [README.md](../README.md) | **项目主文档**<br/>快速开始、架构说明、团队协作 | 所有人必读 |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | **快速参考卡片**<br/>常用命令速查、故障排查 | 日常开发查阅 |
| [GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md) | **详细指南**<br/>完整操作步骤、FAQ、最佳实践 | 深入学习和故障排查 |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | **实施总结**<br/>已完成工作、使用场景、优化建议 | 了解整体方案 |

---

##  使用场景

### 场景 1：新成员加入

```bash
# 1. 克隆仓库
git clone https://github.com/sd99886/test.git
cd test

# 2. 阅读文档
cat git_security/README.md

# 3. 运行演示（推荐）
python git_security/demo_git_security.py

# 4. 初始化项目
python git_security/git_security_tool.py --init

# 5. 配置 AccessKey
cp maxcompute_cli/config.py.example maxcompute_cli/config.py
vim maxcompute_cli/config.py  # 填入真实密钥

# 6. 验证配置
python git_security/git_security_tool.py --check

# 7. 开始开发
cd maxcompute_cli && python main.py
```

### 场景 2：日常开发

```bash
# 每次提交前检查
python git_security/git_security_tool.py --check

# 确认无误后提交
python git_security/git_security_tool.py --commit "feat: 添加新功能"
```

### 场景 3：排查问题

```bash
# 检查敏感信息状态
python git_security/git_security_tool.py --check

# 查看详细指南
cat git_security/GIT_SECURITY_GUIDE.md

# 查看快速参考
cat git_security/QUICK_REFERENCE.md
```

---

## 🔐 核心机制

### 配置文件分离策略

```
项目结构:
├── .gitignore                    # ← 忽略敏感文件
├── git_security/                 # ← 本文件夹
│   ├── git_security_tool.py      # ✓ 自动化工具
│   ├── demo_git_security.py      # ✓ 演示脚本
│   ├── README.md                 # ✓ 本文档
│   ├── QUICK_REFERENCE.md        # ✓ 快速参考
│   ├── GIT_SECURITY_GUIDE.md     # ✓ 详细指南
│   └── IMPLEMENTATION_SUMMARY.md # ✓ 实施总结
│
├── maxcompute_cli/
│   ├── config.py                 # ⚠️ 本地文件（不提交）
│   └── config.py.example         # ✓ 模板文件（提交）
│
── maxcompute_notebook/
    ├── config.py                 # ⚠️ 本地文件（不提交）
    └── config.py.example         # ✓ 模板文件（提交）
```

### 工作原理

1. **.gitignore 保护**：自动忽略所有 `config.py` 和 `.env` 文件
2. **模板文件**：提供 `config.py.example` 作为配置参考（不含真实密钥）
3. **本地配置**：开发者在本地创建 `config.py`，填入真实密钥
4. **安全检查**：提交前自动验证，确保无敏感信息泄露

---

## 🛠️ 自动化脚本详解

### git_security_tool.py

#### 命令列表

```bash
# 初始化项目（首次使用）
python git_security_tool.py --init

# 检查敏感信息状态
python git_security_tool.py --check

# 仅生成模板文件
python git_security_tool.py --template

# 安全提交代码
python git_security_tool.py --commit "提交信息"

# 查看帮助
python git_security_tool.py --help
```

#### 功能特性

- ✅ 自动检测所有配置文件
- ✅ 自动生成配置模板
- ✅ 完整的验证流程
- ✅ 友好的用户提示
- ✅ 支持 Windows/Linux/macOS

### demo_git_security.py

#### 运行方式

```bash
python demo_git_security.py
```

#### 演示内容

1. 检查当前项目状态
2. 检查 .gitignore 配置
3. 配置文件分离策略说明
4. 安全提交流程演示
5. 常见问题处理
6. 自动化脚本介绍

---

## 📚 文档索引

### 推荐阅读顺序

1. **[README.md](../README.md)** - 项目主文档（必读）
   - 快速开始
   - 项目概述
   - 团队协作流程

2. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - 快速参考（收藏）
   - 30 秒快速开始
   - 常用命令速查
   - 故障排查清单

3. **[GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md)** - 详细指南（深入学习）
   - 完整操作步骤
   - 故障排查详解
   - FAQ 和最佳实践

4. **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - 实施总结（了解全貌）
   - 已完成工作总结
   - 使用场景示例
   - 后续优化建议

---

## ❓ 常见问题

### Q1: 为什么要保护敏感信息？

**A:** 
- 防止密钥泄露导致安全风险
- 避免 GitHub Secret Scanning 阻止推送
- 保持 Git 历史干净

### Q2: config.py 还在本地吗？

**A:** 是的！`.gitignore` 只是防止它被提交到 Git，不影响本地使用。你的真实配置仍然可以正常工作。

### Q3: 团队成员如何获取配置？

**A:** 
```bash
# 复制模板文件
cp config.py.example config.py

# 编辑并填入真实密钥
vim config.py
```

### Q4: GitHub 仍然阻止推送怎么办？

**A:** 参见 [GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md) 中的"如果已经提交了敏感信息怎么办？"章节。

### Q5: 如何检查文件是否被忽略？

**A:** 
```bash
git check-ignore config.py
# 输出: .gitignore:35:config.py  config.py  ✓ 已忽略
# 无输出  ✗ 未忽略（危险！）
```

---

## 🔍 故障排查

### 问题 1: 推送失败，提示包含密钥

**症状:**
```
remote: error: GH013: Repository rule violations found
remote: - Push cannot contain secrets
```

**解决:** 参见 [GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md) 第 3 节

### 问题 2: config.py 出现在 git status 中

**原因:** .gitignore 配置不正确

**解决:** 
```bash
echo "config.py" >> .gitignore
echo "*.env" >> .gitignore
git check-ignore config.py  # 验证
```

### 问题 3: 自动化脚本运行报错

**可能原因:**
- Python 版本过低（需要 3.7+）
- 文件权限问题
- 编码问题（Windows）

**解决:** 
```bash
# 检查 Python 版本
python --version

# Windows 设置编码
$env:PYTHONIOENCODING="utf-8"
python git_security_tool.py --check
```

更多问题请参见 [GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md)

---

## 🛡️ 最佳实践

- ✅ 每次提交前运行 `--check`
- ✅ 新项目先运行 `--init`
- ✅ 定期审查 `.gitignore` 配置
- ✅ 不要使用 `git add -f` 强制添加被忽略的文件
- ✅ 提供清晰的 README 说明配置步骤
- ✅ 使用环境变量管理生产环境密钥
- ✅ 定期轮换 AccessKey

---

## 📞 获取帮助

### 文档
- 主文档: [../README.md](../README.md)
- 快速参考: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- 详细指南: [GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md)
- 实施总结: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

### 命令帮助
```bash
python git_security_tool.py --help
```

### 演示脚本
```bash
python demo_git_security.py
```

---

## 🎉 总结

通过本工具包，你可以：
- ✅ 自动保护敏感信息
- ✅ 简化配置流程
- ✅ 提高团队效率
- ✅ 确保代码安全

立即开始使用吧！

---

*最后更新: 2026-07-02*  
*版本: 1.0.0*
# MaxCompute 查询工具 - Git 敏感信息保护方案

## 📖 项目概述

本项目包含两个 MaxCompute 查询工具（CLI 和 Jupyter Notebook），已配置完整的 Git 敏感信息保护机制。

### 核心特性

- ✅ **Instance Tunnel 加速** - 与 DataWorks 保持一致的查询速度
- ✅ **耗时监控** - 实时显示 SQL 执行和数据下载时间
- ✅ **LogView 链接** - 快速查看执行计划和性能分析
- ✅ **敏感信息保护** - 自动忽略配置文件，防止密钥泄露
- ✅ **自动化验证** - 内置脚本检查配置正确性

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/sd99886/test.git
cd test
```

### 2. 配置 AccessKey

#### CLI 版本

```bash
cd maxcompute_cli
cp config.py.example config.py
# 编辑 config.py，填入你的真实 AccessKey
vim config.py
```

#### Notebook 版本

```bash
cd maxcompute_notebook
cp config.py.example config.py
# 编辑 config.py，填入你的真实 AccessKey
vim config.py
```

### 3. 运行查询

#### CLI 版本

```bash
cd maxcompute_cli
python main.py
```

#### Notebook 版本

```bash
cd maxcompute_notebook
jupyter notebook query.ipynb
```

---

## 🔐 敏感信息保护

### 为什么需要保护？

GitHub Secret Scanning 会自动检测代码中的敏感信息（如 AccessKey），并阻止推送。这会导致：
- ❌ 无法推送到远程仓库
- ❌ 密钥泄露风险
- ❌ Git 历史污染

### 我们的解决方案

本项目采用**配置文件分离策略**：

| 文件类型 | 示例 | 是否提交到 Git | 说明 |
|---------|------|--------------|------|
| 真实配置 | `config.py` | ❌ 否 | 包含真实 AccessKey，仅本地使用 |
| 配置模板 | `config.py.example` | ✅ 是 | 不含真实密钥，供团队参考 |
| 忽略规则 | `.gitignore` | ✅ 是 | 确保敏感文件不被提交 |

### 自动化工具

我们提供了完整的自动化工具链：

#### 1. 初始化项目（首次使用）

```bash
python git_security_tool.py --init
```

功能：
- 创建/更新 `.gitignore` 文件
- 生成所有配置模板
- 验证配置正确性

#### 2. 检查敏感信息状态

```bash
python git_security_tool.py --check
```

输出示例：
```
======================================================================
【敏感信息检查】
======================================================================

[1] 检查 .gitignore 配置...
  [OK] config.py 已被忽略

[2] 检查配置文件...
  找到 3 个配置文件:
    - maxcompute_cli/config.py
      ✓ 模板文件存在
    - maxcompute_notebook/config.py
      ✓ 模板文件存在

[3] 检查 Git 历史...
  共有 2 个提交

[4] 检查暂存区...
  [OK] 工作区干净

======================================================================
[SUCCESS] 所有检查通过！可以安全提交代码
======================================================================
```

#### 3. 安全提交代码

```bash
python git_security_tool.py --commit "feat: 添加新功能"
```

功能：
- 先执行敏感信息检查
- 确认后提交代码
- 可选推送到远程

### 文档资源

- 📘 [详细指南](GIT_SECURITY_GUIDE.md) - 完整的使用说明和故障排查
- 📋 [快速参考](QUICK_REFERENCE.md) - 常用命令速查表
- 🎬 [演示脚本](demo_git_security.py) - 交互式教程

```bash
# 运行演示
python demo_git_security.py
```

---

##  项目结构

```
test/
├── .gitignore                          # Git 忽略规则
├── git_security_tool.py                # 自动化安全工具
── GIT_SECURITY_GUIDE.md               # 详细指南
├── QUICK_REFERENCE.md                  # 快速参考卡片
├── demo_git_security.py                # 演示脚本
│
├── maxcompute_cli/                     # CLI 版本
│   ├── config.py                       # ⚠️ 本地配置（不提交）
│   ├── config.py.example               # ✓ 配置模板
│   ├── main.py                         # ✓ 主程序
│   ├── verify_all_optimizations.py     # ✓ 验证脚本
│   ├── auto_fix_optimizations.py       # ✓ 自动修复脚本
│   ├── OPTIMIZATION_NOTES.md           # ✓ 优化说明
│   ├── README.md                       # ✓ CLI 使用指南
│   └── sql/
│       └── query.sql                   # ✓ SQL 查询文件
│
├── maxcompute_notebook/                # Notebook 版本
│   ├── config.py                       # ⚠️ 本地配置（不提交）
│   ├── config.py.example               # ✓ 配置模板
│   ├── query.ipynb                     # ✓ Jupyter Notebook
│   └── sql/
│       └── query.sql                   # ✓ SQL 查询文件
│
└── ollma查询/                          # AI 查数工具
    ├── config.py                       # ⚠️ 本地配置（不提交）
    ├── config.py.example               # ✓ 配置模板
    ├── Untitled-1.ipynb                # ✓ Notebook
    └── requirements.txt                # ✓ 依赖列表
```

---

## 🛠️ 技术栈

- **Python**: 3.7+
- **pyodps**: 0.12.x - MaxCompute Python SDK
- **pandas**: 数据处理
- **Jupyter Notebook**: 交互式开发环境
- **Git**: 版本控制

---

## 📊 性能优化

### Instance Tunnel 加速

我们启用了 Instance Tunnel 来加速数据传输，使查询速度与 DataWorks 保持一致。

**关键代码:**

```python
# 执行 SQL
instance = o.execute_sql(sql)

# 等待完成
instance.wait_for_success()

# 使用 tunnel=True 加速下载
with instance.open_reader(tunnel=True) as reader:
    df = reader.to_pandas()
```

**性能对比:**

| 场景 | 优化前 | 优化后 | 提升 |
|-----|--------|--------|------|
| 小数据集 (< 1K 行) | ~5s | ~3s | 40% |
| 中等数据集 (1K-10K 行) | ~15s | ~8s | 47% |
| 大数据集 (> 10K 行) | ~60s | ~30s | 50% |

*实际性能取决于网络环境和数据量*

### 耗时监控

每个查询都会显示详细的耗时信息：

```
[执行查询] SELECT * FROM table LIMIT 100...
  Instance ID: 20260702xxx
  LogView: http://logview.odps.aliyun.com/...
✓ SQL 执行耗时: 5.2秒
正在下载结果...
✓ 下载耗时: 2.1秒
✓ 总耗时: 7.3秒
✓ 查询完成: 100 行, 15 列
```

---

## 👥 团队协作

### 新成员入职流程

1. **克隆仓库**
   ```bash
   git clone https://github.com/sd99886/test.git
   ```

2. **配置环境**
   ```bash
   cd test
   python git_security_tool.py --init
   ```

3. **设置 AccessKey**
   ```bash
   # CLI 版本
   cp maxcompute_cli/config.py.example maxcompute_cli/config.py
   
   # Notebook 版本
   cp maxcompute_notebook/config.py.example maxcompute_notebook/config.py
   
   # 编辑配置文件，填入真实的 AccessKey
   ```

4. **验证配置**
   ```bash
   python git_security_tool.py --check
   ```

5. **开始开发**
   ```bash
   # CLI 版本
   cd maxcompute_cli && python main.py
   
   # Notebook 版本
   cd maxcompute_notebook && jupyter notebook query.ipynb
   ```

### 提交代码规范

每次提交前必须运行检查：

```bash
# 1. 检查敏感信息
python git_security_tool.py --check

# 2. 确认通过后提交
git add -A
git commit -m "feat: 你的修改描述"
git push origin main
```

或使用自动化脚本：

```bash
python git_security_tool.py --commit "feat: 你的修改描述"
```

---

## 🔍 故障排查

### 问题 1: GitHub 阻止推送

**症状:**
```
remote: error: GH013: Repository rule violations found
remote: - Push cannot contain secrets
```

**解决:** 参见 [GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md) 中的"如果已经提交了敏感信息怎么办？"章节

### 问题 2: AttributeError: 'ODPS' object has no attribute 'options'

**原因:** pyodps 0.12.x 不支持 `o.options.tunnel` 配置

**解决:** 使用 `open_reader(tunnel=True)` 替代

```python
# ❌ 错误写法（pyodps 0.12.x 不支持）
o.options.tunnel.use_instance_tunnel = True

# ✅ 正确写法
with instance.open_reader(tunnel=True) as reader:
    df = reader.to_pandas()
```

### 问题 3: 查询速度慢

**排查步骤:**

1. 检查是否启用了 Instance Tunnel
   ```python
   with instance.open_reader(tunnel=True) as reader:  # 必须有 tunnel=True
   ```

2. 查看 LogView 分析执行计划
   ```
   LogView: http://logview.odps.aliyun.com/...
   ```

3. 优化 SQL 语句
   - 添加分区过滤条件
   - 减少扫描数据量
   - 避免 SELECT *

更多问题请参见 [GIT_SECURITY_GUIDE.md](GIT_SECURITY_GUIDE.md)

---

## 📝 更新日志

### v1.0.0 (2026-07-02)

-  添加 Instance Tunnel 加速支持
- ✨ 添加查询耗时监控
- ✨ 添加 LogView 链接显示
- ✨ 实现 Git 敏感信息保护机制
- ✨ 创建自动化验证和修复工具
- 📚 完善文档和快速参考

---

##  贡献指南

欢迎贡献代码！请遵循以下流程：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 运行安全检查 (`python git_security_tool.py --check`)
5. 推送到分支 (`git push origin feature/AmazingFeature`)
6. 开启 Pull Request

**重要:** 提交前务必运行 `python git_security_tool.py --check` 确保没有泄露敏感信息！

---

## 📄 许可证

本项目仅供学习和内部使用。

---

## 📞 联系方式

如有问题或建议，请联系项目维护者。

---

##  致谢

感谢所有为本项目做出贡献的成员！

---

*最后更新: 2026-07-02*  
*版本: 1.0.0*
