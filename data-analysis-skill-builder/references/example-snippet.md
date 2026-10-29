# 填写示例片段

> 本文档提供脱敏后的真实填写样例，作为从模板到实际内容的参照物。  
> 所有表名、字段名、数据均已脱敏，仅展示格式和思路。

---

## L2 原子方法填写示例：MTD-04 前后对比（换货率场景）

````markdown
### MTD-04 前后对比

- **触发：** "换货率变化""切换后效果""新尺码表上线前后""策略调整效果"
- **适用表：** T_EXCHANGE_SNAPSHOT（换货快照表）、T_ORDER_SNAPSHOT（订单快照表）
- **参数：** 事件日期（${event_date}）、前窗口天数（${pre_days}）、后窗口天数（${post_days}）、分组维度（${dim}）
- **步骤：**
  1. 校验前后窗口等长（${pre_days} == ${post_days}），剔除大促日（如 618/双11）
  2. 分别计算前后窗口的换货单数和订单数
  3. 算换货率变化量和变化率
  4. 若所有维度值同向变化，标记为"疑似季节性因素"，建议改用 DID 方法
- **伪 SQL：**

\```sql
SELECT  CASE WHEN SUBSTR(order_date, 1, 10) < '${event_date}' THEN '前' ELSE '后' END AS period,
        COUNT(DISTINCT exchange_order_no) AS exchange_cnt,
        COUNT(DISTINCT order_no) AS order_cnt,
        ROUND(COUNT(DISTINCT exchange_order_no) * 100.0
              / NULLIF(COUNT(DISTINCT order_no), 0), 2) AS exchange_rate_pct
FROM    T_EXCHANGE_SNAPSHOT
WHERE   SUBSTR(order_date, 1, 10) BETWEEN '${start}' AND '${end}'
GROUP BY CASE WHEN SUBSTR(order_date, 1, 10) < '${event_date}' THEN '前' ELSE '后' END;
\```

- **输出：** 前后两期换货率对比表 + 变化率百分比
- **陷阱：** ①窗口不等长导致基数不同；②跨大促日导致异常波动；③比率指标不可对率值求平均，应分子分母分别聚合后再除
- **特别提示：** 若发现所有站点换货率同步下降 2-3pp，大概率是季节性因素（如夏季换货率天然低于冬季），不要直接归因于策略变更。应补充业务特有的 DID（同比差分）方法剥离季节性后再下结论。
````

**要点解读：**

- **触发**写了口语化表达（"切换后效果"）和专业术语（"策略调整效果"），确保意图识别不漏
- **适用表**用了 L0 定义的表 ID 别名，不写真实表名
- **步骤**包含了校验逻辑（窗口等长、剔除大促），不只是"算一下"
- **伪 SQL**用 `${参数}` 占位，不含任何硬编码值
- **陷阱**列出了 3 个具体易错点，不是泛泛的"注意数据质量"
- **特别提示**给出了业务判断规则（同步下降 → 季节性），帮助 agent 避免过度归因

---

## L3 场景配置填写示例

### 表格形式

| 场景 ID | 场景名称     | 触发词                        | 方法链                      | 维度          | 指标                      | 必需输入                           | 固化查询  | 备注                         |
| ----- | -------- | -------------------------- | ------------------------ | ----------- | ----------------------- | ------------------------------ | ----- | -------------------------- |
| S03   | 换货率前后对比  | 换货率变化、切换后效果、新尺码表上线后、策略调整效果 | MTD-01 → MTD-04 → MTD-02 | site_code   | M_EXCH_RATE             | —                              | —     | 新尺码表 2026-09-08 上线，数据从该日起算 |
| S05   | 品类换货排行   | 哪些品类换货多、换货Top品类、品类换货排行     | MTD-01 → MTD-02          | category_l2 | M_EXCH_CNT, M_EXCH_RATE | —                              | FQ-01 | —                          |
| S08   | 活动商品转化分析 | 活动商品转化率、这批SKU表现怎么样         | MTD-01 → MTD-02          | sku_code    | M_CVR, M_GMV            | 文件: 活动SKU清单（Excel/CSV，需含商品编码列） | —     | —                          |
| S09   | 目标达成监控   | 换货率达标了吗、超过目标值了吗            | MTD-01 → MTD-03          | site_code   | M_EXCH_RATE             | 目标值: 换货率阈值（百分比数值，如 15）         | —     | —                          |

### YAML 形式（新增场景时用）

```yaml
场景ID: S08
场景名: 活动商品转化分析
触发词: [活动商品转化率, 这批SKU表现怎么样, 帮我看看活动款]
方法链: [MTD-01, MTD-02]
维度: sku_code
指标: [M_CVR, M_GMV]
必需输入: "文件: 活动SKU清单（Excel/CSV，需含商品编码列）"
固化查询: ""
备注: ""
```

**要点解读：**

- **触发词**同时包含术语（"渠道×品类交叉"）和口语（"哪个渠道什么品类换货高"）
- **方法链**标注了每步的作用：MTD-01 取基线 → MTD-06 交叉分析 → MTD-02 排行定位
- **必需输入**明确写出需要什么数据和语义要求（如"Excel/CSV，需含商品编码列"），agent 据此向用户索取文件，并在收到文件后动态识别实际列名。S03/S05 无需额外输入填 "—"
- **备注**是补充说明性质（如数据起始日期、版本覆盖范围），不是 agent 必须等待的前置条件
- **参数不写在 L3**：时间窗口、过滤条件、体量门槛等由 L2 方法定义，agent 执行时根据方法和用户输入动态绑定

---

## L0 warehouse_schema.md 枚举值填写示例

```markdown
**exchange_type（换货类型）**

| 值 | 含义 | 占比 |
|----|------|------|
| size_exchange | 尺码换货 | 62.3% |
| color_exchange | 颜色换货 | 18.7% |
| style_exchange | 款式换货 | 12.1% |
| defect_exchange | 质量问题换货 | 6.9% |

> ⚠️ `defect_exchange` 占比低但业务敏感度高，分析时建议单独关注，不要被整体均值淹没。
```

**要点解读：**

- 占比来自真实 DISTINCT 查询结果，不是凭记忆估算
- 附带业务解读（低占比但高敏感度），帮助 agent 理解数据背后的业务含义

---

## metrics_definitions.md 陷阱填写示例

```markdown
## 常见计算陷阱

1. **实体 ID 混淆**：统计换货单数用 `COUNT(DISTINCT exchange_order_no)`，统计原始订单数用 `COUNT(DISTINCT order_no)`。两者不可互换——一个订单可能对应多个换货单。
2. **粒度膨胀**：换货明细表是一行/一件商品，`COUNT(1)` 会把同一换货单的多件商品重复计数。必须用 `COUNT(DISTINCT exchange_order_no)` 去重。
3. **快照表时间过滤**：换货快照表是全量表，用 `SUBSTR(order_date, 1, 10) BETWEEN` 过滤，不要用 `pt BETWEEN`（该表无分区字段）。
4. **比率分母为零**：某些品类在某时间窗口内可能零订单，计算换货率时分母必须用 `NULLIF(..., 0)` 防除零。
5. **组合品 NULL 干扰**：`combo_flag` 字段仅组合品有值，非组合品为 NULL。分析组合品占比时必须先 `WHERE combo_flag IS NOT NULL` 或在分母中排除 NULL。
```

**要点解读：**

- 每条陷阱都有具体的字段名和操作方式，不是泛泛的"注意数据质量"
- 包含了"怎么做"（用 NULLIF）和"为什么"（分母为零会报错或被吞掉）

---

## fixed_queries.md 固化查询填写示例

````markdown
## FQ-01 各站点换货率排行（近30天）

- **场景名称：** 各站点换货率排行
- **关联场景 ID：** S05
- **验证日期：** 2026-09-15
- **参数说明：**

| 参数 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| ${start_date} | STRING | 查询起始日期（YYYY-MM-DD） | 2026-08-16 |
| ${end_date} | STRING | 查询结束日期（YYYY-MM-DD） | 2026-09-14 |
| ${top_n} | INT | 返回前 N 个站点 | 10 |
| ${min_orders} | INT | 体量门槛（最小订单数） | 100 |

- **SQL：**

\```sql
-- 各站点换货率排行（近30天）
-- 关联场景: S05 | 验证日期: 2026-09-15
SELECT  site_code,
        COUNT(DISTINCT exchange_order_no) AS exchange_cnt,
        COUNT(DISTINCT order_no) AS order_cnt,
        ROUND(COUNT(DISTINCT exchange_order_no) * 100.0
              / NULLIF(COUNT(DISTINCT order_no), 0), 2) AS exchange_rate_pct
FROM    dwd_exchange_detail_snapshot
WHERE   SUBSTR(order_date, 1, 10) BETWEEN '${start_date}' AND '${end_date}'
GROUP BY site_code
HAVING  COUNT(DISTINCT order_no) >= ${min_orders}
ORDER BY exchange_rate_pct DESC
LIMIT   ${top_n};
\```

- **输出解读：** 返回各站点换货率排行。关注 exchange_rate_pct > 15% 的行，这些站点的尺码问题可能需要优先排查。
````

**要点解读：**

- **验证信息完整**：验证日期 + 验证人，方便追溯和定期复审
- **参数名与 L2 一致**：`${start_date}`、`${end_date}` 等命名与 MTD-02 的参数定义保持一致
- **所有运行时变量都参数化**：时间范围、Top N、体量门槛全部用 `${param}` 占位，没有硬编码值
- **SQL 注释头**：开头注明关联场景和验证日期，排查问题时能快速定位
- **输出解读具体**：不是"看结果"，而是"关注 > 15% 的行"，帮助 agent 正确解读

---

## fixed_queries.md FILE_LIST 参数示例（文件型输入）

````markdown
## FQ-02 活动商品转化分析

- **场景名称：** 活动商品转化分析
- **关联场景 ID：** S08
- **验证日期：** 2026-10-01
- **参数说明：**

| 参数 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| ${start_date} | STRING | 查询起始日期（YYYY-MM-DD） | 2026-09-01 |
| ${end_date} | STRING | 查询结束日期（YYYY-MM-DD） | 2026-09-30 |
| ${sku_list} | FILE_LIST | 活动SKU清单（语义：商品编码） | 运行时从用户上传文件动态提取 |

- **SQL：**

\```sql
-- 活动商品转化分析
-- 关联场景: S08 | 验证日期: 2026-10-01
-- 前置（agent 运行时动态执行，不在此处预定义）：
--   1. Python 探查文件结构，识别目标列（如 sku_code / item_id / 商品编码）
--   2. 向用户确认目标列
--   3. 提取值列表，创建临时表 tmp_s08_input 并插入数据

SELECT  t.sku_code,
        COUNT(DISTINCT t.order_no) AS order_cnt,
        SUM(t.gmv) AS total_gmv,
        ROUND(COUNT(DISTINCT t.order_no) * 100.0
              / NULLIF(COUNT(DISTINCT t.session_id), 0), 2) AS cvr_pct
FROM    dwd_order_detail t
JOIN    tmp_s08_input i ON t.sku_code = i.sku_code
WHERE   SUBSTR(t.order_date, 1, 10) BETWEEN '${start_date}' AND '${end_date}'
GROUP BY t.sku_code
ORDER BY total_gmv DESC;

-- 后置（agent 运行时执行）：DROP TEMPORARY TABLE IF EXISTS tmp_s08_input;
\```

- **输出解读：** 返回每个活动 SKU 的订单数、GMV 和转化率。关注 cvr_pct < 2% 的 SKU，可能存在详情页体验问题。
````

**要点解读：**

- **不预定义列名和解析代码**：不同用户在不同时间上传的文件列名可能不同（`sku_code` / `item_id` / `商品编码`），agent 在每次收到文件时先探查列名、向用户确认目标列，再动态生成 Python 解析代码和建表语句
- **L3 "必需输入"只描述语义**：写 `文件: 活动SKU清单（Excel/CSV，需含商品编码列）` 而非 `需含 sku_code 列`，让 agent 有空间智能匹配实际列名
- **临时表 JOIN 而非 IN 子句**：500~5000 个 SKU 下稳定高效，不受 IN 子句 1000 条限制
- **固化查询模板只写 JOIN 结构**：临时表的创建、插入、清理都由 agent 在运行时根据实际文件动态生成和执行，模板中只保留注释说明
- **临时表命名带场景前缀**：`tmp_s08_input` 避免多场景并发时表名冲突，查询完成后立即 DROP 清理
