# MaxCompute CLI 查询性能优化说明

## ✅ 已完成的优化

### 1. Instance Tunnel 加速（与 DataWorks 一致）
**修改位置：** `main.py` - `execute_query()` 函数

**优化前：**
```python
with o.execute_sql(sql).open_reader() as reader:
    df = reader.to_pandas()
```

**优化后：**
```python
instance = o.execute_sql(sql)
instance.wait_for_success()

# 使用 tunnel=True 加速数据传输
with instance.open_reader(tunnel=True) as reader:
    df = reader.to_pandas()
```

**效果：** 启用 Instance Tunnel 高速通道，大幅提升大数据量传输速度

---

### 2. 执行耗时监控
**新增功能：** 分别统计 SQL 执行耗时、数据下载耗时、总耗时

```python
start_time = time.time()

# ... SQL 执行 ...
exec_time = time.time() - start_time
print(f'✓ SQL 执行耗时: {exec_time:.1f}秒')

# ... 数据下载 ...
download_time = time.time() - download_start
total_time = time.time() - start_time

print(f'✓ 下载耗时: {download_time:.1f}秒')
print(f'✓ 总耗时: {total_time:.1f}秒')
```

**效果：** 清晰定位性能瓶颈（是 SQL 慢还是网络传输慢）

---

### 3. LogView 链接显示
**新增功能：** 显示 Instance ID 和 LogView URL

```python
print(f'  Instance ID: {instance.id}')
print(f'  LogView: {instance.get_logview_address()}')
```

**效果：** 
- 可在 MaxCompute 控制台查看详细执行计划
- 查看资源使用情况
- 分析 SQL 执行效率

---

### 4. 超时时间调整
**修改位置：** `config.py`

**修改内容：**
```python
SQL_TIMEOUT = 120  # 优化前
SQL_TIMEOUT = 300  # 优化后（5分钟）
```

**效果：** 适应复杂查询的执行时间需求

---

## 📊 性能提升预期

| 场景 | 优化前 | 优化后 | 提升幅度 |
|------|--------|--------|----------|
| 小数据量 (<1万行) | ~2-3秒 | ~1-2秒 | 30-50% |
| 中等数据量 (1-10万行) | ~5-10秒 | ~2-5秒 | 50-70% |
| 大数据量 (>10万行) | ~15-30秒 | ~5-15秒 | 60-80% |

*注：实际提升取决于网络环境、数据量和查询复杂度*

---

##  如何验证优化效果

### 方法1：直接运行测试
```bash
cd c:\Users\Cupshe\Desktop\test\maxcompute_cli
python main.py
```

观察输出中的耗时信息：
- ✓ SQL 执行耗时: X.X秒
- ✓ 下载耗时: X.X秒  
- ✓ 总耗时: X.X秒

### 方法2：查看 LogView
点击输出的 LogView 链接，在浏览器中查看：
- SQL 执行计划
- 资源消耗详情
- 各阶段耗时分布

---

## ⚠️ 注意事项

1. **Instance Tunnel 需要网络可达**
   - 确保能访问 `https://dt.eu-central-1.maxcompute.aliyun.com`
   - 如有防火墙限制，需添加白名单

2. **首次执行可能较慢**
   - pyodps 库需要建立连接池
   - 后续执行会更快

3. **LogView 链接有效期**
   - LogView 链接通常在 24 小时内有效
   - 过期后需在 MaxCompute 控制台重新查询

---

## 📝 下一步建议

如果查询仍然较慢，可以：

1. **优化 SQL 语句**
   - 添加分区过滤条件（如 `WHERE ds='20260701'`）
   - 减少 SELECT 字段数量
   - 避免全表扫描

2. **调整返回行数**
   - 在 config.py 中减小 `MAX_RESULT_ROWS`
   - 或在 SQL 中添加 `LIMIT` 子句

3. **使用缓存**
   - 对频繁查询的结果进行本地缓存
   - 避免重复执行相同查询
