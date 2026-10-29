# 固化查询库

---

## FQ-01 {{SCENARIO_NAME}}

- **场景名称：** {{SCENARIO_NAME}}（用户能理解的业务描述，如"各站点换货率排行"）
- **关联场景 ID：** {{SCENE_ID}}（如 S03，agent 内部引用用）
- **验证日期：** {{VERIFY_DATE}}（如 2026-09-15）
- **参数说明：**

| 参数             | 类型       | 说明                 | 示例值         |
| -------------- | -------- | ------------------ | ----------- |
| ${start_date}  | STRING   | 查询起始日期（YYYY-MM-DD） | 2026-09-01  |
| ${end_date}    | STRING   | 查询结束日期（YYYY-MM-DD） | 2026-09-30  |
| {{PARAM_NAME}} | {{TYPE}} | {{DESC}}           | {{EXAMPLE}} |
| ${sku_list}    | FILE_LIST | 活动SKU清单（语义：商品编码） | 运行时从用户上传文件动态提取 |

> **FILE_LIST 类型说明**：该参数来源于 L3 场景"必需输入"列中声明的用户上传文件。Agent 在运行时探查文件结构、确认目标列、用 Python 提取值、动态创建 ODPS 临时表后通过 JOIN 关联（不使用 IN 子句）。解析代码和建表语句不在本文件中预定义，由 agent 根据实际文件动态生成。详见 architecture-guide.md §文件输入协议。

- **SQL：**

```sql
-- {{SCENARIO_NAME}}
-- 关联场景: {{SCENE_ID}} | 验证日期: {{VERIFY_DATE}}
-- 前置（agent 运行时动态执行，不在此处预定义）：
--   1. Python 解析用户上传文件，识别并确认目标列
--   2. 提取值列表，创建临时表 tmp_{{SCENE_ID}}_input 并插入数据

SELECT  t.{{DIM}}, SUM(t.{{MEASURE}}) AS qty
FROM    {{TABLE}} t
JOIN    tmp_{{SCENE_ID}}_input i ON t.{{JOIN_KEY}} = i.{{JOIN_KEY}}
WHERE   {{TIME_FIELD}} BETWEEN '${start_date}' AND '${end_date}'
GROUP BY t.{{DIM}}
ORDER BY qty DESC;

-- 后置（agent 运行时执行）：DROP TEMPORARY TABLE IF EXISTS tmp_{{SCENE_ID}}_input;
```

- **输出解读：** {{HOW_TO_READ_RESULT}}（如：返回各站点换货率排行，关注 pct > 15% 的行）

---

## FQ-02 {{SCENARIO_NAME_2}}
