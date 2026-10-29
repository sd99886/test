# 指标口径与计算逻辑

> 聚焦 {{N}} 大分析场景：{{SCENARIO_LIST}}。

## 指标速查

| 指标 ID         | 名称              | 公式          | 说明       |
| ------------- | --------------- | ----------- | -------- |
| {{METRIC_ID}} | {{METRIC_NAME}} | {{FORMULA}} | {{NOTE}} |

---

## 场景①：{{SCENARIO_1_NAME}}指标

### 核心维度

| 维度字段          | 含义              | 分析用途        |
| ------------- | --------------- | ----------- |
| {{DIM_FIELD}} | {{DIM_MEANING}} | {{DIM_USE}} |

### 计算示例

**{{SUB_METRIC_NAME}}：**

```sql
SELECT  {{DIM_FIELD}},
        SUM({{MEASURE}}) AS qty,
        COUNT(DISTINCT {{ENTITY_ID}}) AS entity_cnt,
        ROUND(SUM({{MEASURE}}) * 100.0 / SUM(SUM({{MEASURE}})) OVER (), 2) AS pct
FROM    {{TABLE}}
WHERE   {{TIME_FILTER}}
GROUP BY {{DIM_FIELD}}
ORDER BY qty DESC;
```

---

## 场景②：{{SCENARIO_2_NAME}}指标

### 核心维度

| 维度字段          | 含义              | 分析用途        |
| ------------- | --------------- | ----------- |
| {{DIM_FIELD}} | {{DIM_MEANING}} | {{DIM_USE}} |

### 专项指标

| 指标                 | 公式          | 业务含义                 |
| ------------------ | ----------- | -------------------- |
| {{DERIVED_METRIC}} | {{FORMULA}} | {{BUSINESS_MEANING}} |

### 计算示例

```sql
{{EXAMPLE_SQL}}
```

---

## 常见计算陷阱

1. **{{TRAP_1_NAME}}**：{{TRAP_1_DESC}}（如：order_no vs service_order_no 混淆——统计订单数用 COUNT(DISTINCT order_no)，统计售后单数用 COUNT(DISTINCT service_order_no)，不可混用）。
2. **粒度混淆**：明细表是多行/单实体，不可用 COUNT(1) 冒充去重实体数。
3. **NULL 处理**：度量字段可能为 NULL，聚合前用 NVL / COALESCE。
4. **时间字段语义**：{{TIME_SEMANTICS}}（是发生时间还是完成时间）。
5. **比率分母**：分母用 NULLIF 防除零；分子分母必须同度量（次数/人数/会话数不可混用）。
6. **{{TRAP_N_NAME}}**：{{TRAP_N_DESC}}（本业务域特有陷阱，如某字段仅子集有值需先过滤）。
