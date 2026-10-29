# 分析报告输出标准（销售额归因）

> 报告以单文件 HTML 输出，内嵌 CSS + Chart.js 图表，确保清晰直观的可视化展示。

## 一、报告交付五原则

1. **数据说明块必备**：报告开头必须标注三项——数据范围（库表 + 基础过滤条件）、时间范围（本期/环比/同比具体日期窗口）、指标口径（GMV/CVR/达成率等公式与定义）。
2. **图表+表格双展示**：占比结构用环形图，品类/部门排行用水平柱状图，趋势用折线图，涨跌贡献用正负分色柱状图，前后对比用分组柱状图；图表下方附数据明细表格。
3. **建议即业务动作**：销售额归因建议必须是可执行动作（运营动作 / 品类商品策略 / 用户运营三类），果断给结论。禁止把"排查数据方案/核对口径"这类分析师工作写进业务建议。
4. **谨慎询问**：仅在数据口径或分析方案确实模糊时才向用户提问；禁止凭空推测。
5. **自查项单列**：尚需进一步验证的列为"我将自行核实的下一步"。

## 二、HTML 报告结构

报告输出为 `.html` 单文件，内嵌 `<style>` 和 `<script>`（引用 Chart.js CDN），结构如下：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>销售额归因分析报告</title>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    /* 完整 CSS 见 §三 */
  </style>
</head>
<body>
<div class="container">

  <!-- ① 标题 -->
  <div class="header">
    <h1>📊 销售额归因分析报告</h1>
    <div class="subtitle">[本期起始日期] ~ [本期结束日期] | cupshe_bigdata_ads.ads_prod_skc_product_info_di</div>
  </div>

  <!-- ② KPI 卡片（4-6 张：GMV 及环比、销量及环比、平均售价及环比、达成率(仅 S06)、退货率） -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="value">--</div>
      <div class="label">GMV（USD）</div>
      <div class="delta">环比 --%</div>
    </div>
    <div class="kpi-card warn">
      <div class="value">--</div>
      <div class="label">销量（环比）</div>
    </div>
    <div class="kpi-card ok">
      <div class="value">--</div>
      <div class="label">平均售价（环比）</div>
    </div>
    <!-- 按场景增减：详情页UV、CVR、达成率、退货率 -->
  </div>

  <!-- ③ 数据说明（表：数据源/时间窗/口径） -->
  <div class="section">
    <h2>📋 数据说明</h2>
    <table>
      <tr><th>项目</th><th>说明</th></tr>
      <tr><td>数据源</td><td>cupshe_bigdata_ads.ads_prod_skc_product_info_di（SKC 日快照，pt 分区，T+1）</td></tr>
      <tr><td>基础过滤</td><td>在架(调整口径)=1、排除无库存测试款、排除赠品</td></tr>
      <tr><td>本期窗口</td><td>[start] ~ [end]（按 date_str 过滤）</td></tr>
      <tr><td>环比窗口</td><td>[start-1m] ~ [end-1m]（等长）</td></tr>
      <tr><td>GMV 口径</td><td>SUM(sale_amount_usd)，USD</td></tr>
      <tr><td>CVR 口径</td><td>销量/详情页UV（件/人，埋点 UV 覆盖范围有限）</td></tr>
    </table>
  </div>

  <!-- ④ 核心诊断（highlight-box：2-3 句话，含维度与数据） -->
  <div class="section">
    <h2>🎯 核心诊断</h2>
    <div class="highlight-box">
      <strong>根本原因：</strong>[如：本期 GMV 环比 -12.3%，主因是泳衣品类量效应 -8.1%（供给：在架 SKC -15%），贡献整体降幅的 65%]
    </div>
  </div>

  <!-- ⑤ 数据展示（按场景 1-3 组 chart-row + 明细表） -->
  <div class="section">
    <h2>📊 一、涨跌贡献与量价拆解</h2>
    <div class="chart-row">
      <div class="chart-box">
        <h3>品类 GMV 涨跌贡献（Top 拖累 vs Top 驱动）</h3>
        <div class="chart-container"><canvas id="chart_contrib"></canvas></div>
      </div>
      <div class="chart-box">
        <h3>量效应 vs 价效应分解</h3>
        <div class="chart-container"><canvas id="chart_qpv"></canvas></div>
      </div>
    </div>
    <table><!-- 明细：维度 | 本期GMV | 环比% | ΔGMV | 贡献占比 | 量效应 | 价效应 --></table>
  </div>

  <!-- ⑥ 建议（三类型 + 优先级标签） -->
  <div class="section">
    <h2>🛠️ 业务建议</h2>
    <table class="suggestion-table">
      <thead><tr><th>优先级</th><th>建议动作</th><th>类型</th><th>数据依据</th><th>预期效果</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <!-- ⑦ 自查项 -->
  <div class="section">
    <h2>📌 我将自行核实的下一步</h2>
    <table><tr><th>待核实项</th><th>原因</th><th>动作</th></tr></table>
  </div>

  <!-- ⑧ 固化查询提示（条件显示：仅当使用了 fixed_queries.md 中 FQ-XX 时输出本节，否则整节删除） -->
  <div class="section" style="background: linear-gradient(135deg, #e8f0fd 0%, #f0f4ff 100%); border-left: 4px solid #3498db;">
    <h2>🔒 本次使用的固化查询</h2>
    <table>
      <tr><th>查询名称</th><th>验证日期</th></tr>
      <tr><td>[固化查询名称]</td><td>[验证日期]</td></tr>
    </table>
    <p style="margin-top: 12px; color: #555; font-size: 13px;">
      💡 以上查询使用的是已固化的分析逻辑。如果业务规则发生变化或分析逻辑需要调整，可以告诉我"更新 XX 查询"，我会重新验证并更新。
    </p>
  </div>

  <!-- ⑨ 免责声明 -->
  <div class="footer">⚠️ 本报告基于 AI 对当前数据的客观分析生成，仅供决策参考。建议人工复核后再执行。</div>

</div>
<script>
  // 通用初始化函数（canvas 不存在时静默跳过）
  function renderChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    new Chart(canvas, config);
  }
  // 各图表配置见 §四。调用时使用 HTML 中实际存在的 canvas ID。
  // 未输出的图表应同时移除对应 canvas 和初始化调用。
</script>
</body>
</html>
```

## 三、CSS 样式规范

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px; border-radius: 12px; margin-bottom: 24px; }
.header h1 { font-size: 28px; margin-bottom: 8px; }
.header .subtitle { opacity: 0.9; font-size: 14px; }
.section { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.section h2 { font-size: 20px; margin-bottom: 16px; color: #2c3e50; border-left: 4px solid #667eea; padding-left: 12px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
.kpi-card { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); border-radius: 10px; padding: 20px; text-align: center; }
.kpi-card .value { font-size: 32px; font-weight: 700; color: #667eea; }
.kpi-card .label { font-size: 13px; color: #7f8c8d; margin-top: 4px; }
.kpi-card .delta { font-size: 12px; margin-top: 4px; color: #7f8c8d; }
.kpi-card .delta.up { color: #27ae60; }
.kpi-card .delta.down { color: #e74c3c; }
.kpi-card.warn .value { color: #e74c3c; }
.kpi-card.ok .value { color: #27ae60; }
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.chart-box { background: #fafbfc; border-radius: 8px; padding: 16px; }
.chart-box h3 { font-size: 15px; color: #555; margin-bottom: 12px; }
.chart-container { position: relative; height: 280px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: #f8f9fa; padding: 10px 12px; text-align: left; font-weight: 600; color: #555; border-bottom: 2px solid #e9ecef; }
td { padding: 9px 12px; border-bottom: 1px solid #f0f0f0; }
tr:hover td { background: #f8f9fb; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.neg { color: #e74c3c; }
.pos { color: #27ae60; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-red { background: #fde8e8; color: #e74c3c; }
.badge-green { background: #e8f8f0; color: #27ae60; }
.badge-blue { background: #e8f0fd; color: #3498db; }
.highlight-box { background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); border-left: 4px solid #f39c12; padding: 16px; border-radius: 8px; margin-bottom: 16px; }
.highlight-box strong { color: #d35400; }
.suggestion-table th { background: #667eea; color: white; }
.footer { text-align: center; padding: 20px; color: #95a5a6; font-size: 12px; }
@media (max-width: 768px) { .chart-row { grid-template-columns: 1fr; } .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
```

## 四、图表选型与 Chart.js 配置

先在页面中定义一次通用初始化函数（已包含在 §二 的 `<script>` 中）。调用时使用 HTML 中实际存在的 canvas ID；未输出的图表应同时移除对应 canvas 和初始化调用。

```javascript
function renderChart(canvasId, config) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  new Chart(canvas, config);
}
```

### 品类/新老品 GMV 结构占比 → 环形图 (Doughnut)

```javascript
renderChart('chart_structure', {
  type: 'doughnut',
  data: {
    labels: ['成衣', '泳衣', '内睡', 'ACC'],
    datasets: [{ data: [/* 本期 GMV */], backgroundColor: ['#3498db', '#e74c3c', '#f39c12', '#95a5a6'] }]
  },
  options: {
    plugins: {
      legend: { position: 'right' },
      tooltip: { callbacks: { label: (c) => {
        const total = c.dataset.data.reduce((a, b) => a + b, 0);
        const pct = (c.raw / total * 100).toFixed(1);
        return `${c.label}: ${c.raw} (${pct}%)`;
      }}}
    }
  }
});
```

### 品类 GMV 排行 → 水平柱状图 (Bar, indexAxis: 'y')

```javascript
renderChart('chart_rank', {
  type: 'bar',
  data: {
    labels: [/* 二级品类 Top10 */],
    datasets: [{ label: 'GMV', data: [/* 本期 GMV */],
      backgroundColor: ['#e74c3c', '#3498db', '#f39c12', '#95a5a6', '#2ecc71', '#9b59b6'] }]
  },
  options: { indexAxis: 'y', plugins: { legend: { display: false } } }
});
```

### 涨跌贡献（正负分色）→ 柱状图

```javascript
renderChart('chart_contrib', {
  type: 'bar',
  data: {
    labels: [/* 品类/部门 */],
    datasets: [{ label: 'ΔGMV（环比差额）', data: [/* 正负值 */],
      backgroundColor: (c) => c.raw < 0 ? '#e74c3c' : '#27ae60' }]
  },
  options: { plugins: { legend: { display: false } },
    scales: { y: { ticks: { callback: (v) => (v/10000).toFixed(0) + '万' } } } }
});
```

### 量价双因子 → 分组柱状图（量效应 vs 价效应）

```javascript
renderChart('chart_qpv', {
  type: 'bar',
  data: {
    labels: [/* 维度 */],
    datasets: [
      { label: '量效应', data: [/* (q1-q0)*p0 */], backgroundColor: '#e74c3c' },
      { label: '价效应', data: [/* q0*(p1-p0) */], backgroundColor: '#3498db' }
    ]
  }
});
```

### GMV 日/周趋势 → 折线图 (Line)

```javascript
renderChart('chart_trend', {
  type: 'line',
  data: {
    labels: [/* 日期/周 */],
    datasets: [
      { label: '本期', data: [/* GMV */], borderColor: '#e74c3c', tension: 0.3 },
      { label: '环比期', data: [/* 环比 GMV，与本期按序号对齐 */], borderColor: '#3498db', tension: 0.3, borderDash: [5,5] }
    ]
  }
});
```

### 新老品结构（当期 vs 环比）→ 堆叠柱状图

```javascript
renderChart('chart_newold', {
  type: 'bar',
  data: {
    labels: [/* 本期, 环比期 */],
    datasets: [
      { label: '当年新品', data: [/* GMV */], backgroundColor: '#e74c3c' },
      { label: '当年老品', data: [/* GMV */], backgroundColor: '#3498db' },
      { label: '当年未上架', data: [/* GMV */], backgroundColor: '#95a5a6' }
    ]
  },
  options: { scales: { x: { stacked: true }, y: { stacked: true } } }
});
```

### 漏斗转化 → KPI 卡片 + 分组柱状图（各层转化率本期 vs 环比）

```javascript
renderChart('chart_funnel', {
  type: 'bar',
  data: {
    labels: ['CTR', '加车率', 'CVR'],
    datasets: [
      { label: '本期', data: [/* 率 */], backgroundColor: '#3498db' },
      { label: '环比期', data: [/* 率 */], backgroundColor: '#95a5a6' }
    ]
  },
  options: { scales: { y: { ticks: { callback: (v) => (v*100).toFixed(1) + '%' } } } }
});
```

### 部门目标达成 → 水平柱状图（达成率，参考线 100%）

```javascript
renderChart('chart_target', {
  type: 'bar',
  data: {
    labels: [/* 部门 */],
    datasets: [{ label: '达成率', data: [/* 率 */],
      backgroundColor: (c) => c.raw >= 1 ? '#27ae60' : '#e74c3c' }]
  },
  options: { indexAxis: 'y', plugins: { legend: { display: false } },
    scales: { x: { ticks: { callback: (v) => (v*100).toFixed(0) + '%' } } } }
});
```

## 五、图表选型速查

| 分析场景 | 图表类型 | Chart.js type | 适用条件 |
| -------- | ----------- | ----------------------- | ------------ |
| 品类/新老品 GMV 占比 | 环形图 | `doughnut` | 分类 ≤ 6 个 |
| 品类/部门 GMV 排行 | 水平柱状图 | `bar` + `indexAxis:'y'` | Top N 排行 |
| 涨跌贡献 | 正负分色柱状图 | `bar` | ΔGMV 排序 |
| 量价拆解 | 分组柱状图 | `bar` (grouped) | 量效应 vs 价效应 |
| GMV 趋势 | 折线图 | `line` | 时间序列 ≥ 5 个周期 |
| 新老品结构 | 堆叠柱状图 | `bar` + `stacked` | 当期 vs 环比两期 |
| 漏斗转化率 | KPI 卡片 + 分组柱状图 | `kpi-card` + `bar` | 各层率值两期对比 |
| 部门达成率 | 水平柱状图（红绿分色） | `bar` + `indexAxis:'y'` | 目标达成场景 |

## 六、配色方案

| 用途 | 颜色 | 色值 |
| ------ | ---- | --------------------- |
| 负面/下滑/拖累 | 红 | `#e74c3c` |
| 中性/环比期对照 | 蓝 | `#3498db` |
| 正面/增长/达成 | 绿 | `#27ae60` |
| 警告/中等 | 橙 | `#f39c12` |
| 其他/未上架/次要 | 灰 | `#95a5a6` |
| 辅助/老品 | 紫 | `#9b59b6` |
| 主题色 | 渐变蓝紫 | `#667eea` → `#764ba2` |

## 七、表述铁律

| 禁止 | 替代 |
| --------- | ------------------------------ |
| "GMV 下降了，建议优化" | "泳衣品类 GMV 环比 -15.2%（量效应 -8.1pp），在架 SKC -15%，建议优先补货 Top3 畅销款" |
| "转化率有待提升" | "CVR 环比 -0.4pp（件/人），主降环节为加车率 -0.6pp，建议排查详情页主图与尺码表" |
| "可能需要调整" | "建议将 XX 品类在架 SKC 恢复至环比期水平（+N 款），按款效 X USD/款测算可回补 GMV 约 Y 万" |
| "数据不够" | "当前数据仅覆盖 N 天，样本量 M 单，结论仅供参考" |
| "CVR 为 3% 即 3% 用户下单" | "CVR=3% 指 100 个详情页 UV 对应 3 件销量（件/人口径）" |

## 八、建议表格中的优先级标签

| 优先级 | 样式 | 含义 |
| --- | ------------------------------------------- | -------- |
| P0 | `<span class="badge badge-red">P0</span>` | 紧急，需立即处理（如 Top1 拖累品类断货） |
| P1 | `<span class="badge badge-blue">P1</span>` | 重要，本周内处理 |
| P2 | `<span class="badge badge-green">P2</span>` | 改善项，排期处理 |

建议类型标签：`运营动作` / `品类策略` / `用户运营`（badge-blue / badge-red / badge-green 复用）。预估收益规则：能闭环测算的给区间（保守=50%，中性=全额）；不能测算的写"方向性，待测"，禁止编造精确金额。

## 九、数字与文风

- 金额：千分位，保留 2 位小数；大额附万元（÷10000，1 位小数）；单位 USD。
- 比率/环比：百分比，1 位小数；占比变化用"pp / 个百分点"。
- 分母为 0 或 NULL：写 `N/A`，不中断报告。
- 语气：业务汇报体，短句；不说"我认为""也许"。
- 报告正文不出现：SQL、odps-query、脚本路径等过程信息。

## 十、报告重建铁律

1. **每次全量重建**：报告数据必须全部来自当次查询结果。禁止在旧报告文件上修改数字——KPI 卡片、图表、表格三处数据必须一致。
2. **canvas 与 renderChart 配对**：HTML 中每个 `<canvas id="chart_xx">` 都必须有对应的 `renderChart('chart_xx', {...})` 调用。未使用的图表要同时移除 canvas 和 JS 调用。
3. **时间范围用 `date` 命令确认**：生成报告前获取当前日期确认窗口；数据 T+1，"近一周" = 今天减 8 天到昨天（N-8 ~ N-1），end_date 最晚为昨天。
4. **Chart.js 数据禁止硬编码**：图表数据必须来自当次查询结果，禁止把上次查询结果写死在 JS 里。
