# 分析报告输出标准

> 报告以单文件 HTML 输出，内嵌 CSS + Chart.js 图表，确保清晰直观的可视化展示。

## 一、报告交付五原则

1. **数据说明块必备**：报告开头必须标注三项——数据范围（库表+筛选条件）、时间范围（具体日期窗口）、指标口径（公式与定义）。
2. **图表+表格双展示**：分布/占比类用饼图或环形图，排行/对比类用柱状图，趋势类用折线图；图表下方附数据明细表格。
3. **建议即产品动作**：{{ACTION_TYPE}}建议必须是基于数据判断后给出的可执行动作，果断给结论。禁止把"排查数据方案/核对口径"这类分析师工作写进业务建议。
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
  <title>{{DOMAIN_LABEL}}分析报告</title>
  
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    /* 完整 CSS 见 §三 */
  </style>
</head>
<body>
<div class="container">

  
  <div class="header">
    <h1>📊 {{DOMAIN_LABEL}}分析报告</h1>
    <div class="subtitle">[起始日期] ~ [结束日期] | [库表名]</div>
  </div>

  
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="value">--</div>
      <div class="label">{{KPI_LABEL_1}}</div>
    </div>
    <div class="kpi-card warn">
      <div class="value">--</div>
      <div class="label">{{KPI_LABEL_2}}（需关注）</div>
    </div>
    <div class="kpi-card ok">
      <div class="value">--</div>
      <div class="label">{{KPI_LABEL_3}}（正常）</div>
    </div>
    
  </div>

  
  <div class="section">
    <h2>🎯 核心诊断</h2>
    <div class="highlight-box">
      <strong>根本原因：</strong>[2-3 句话总结，包含具体维度与数据]
    </div>
  </div>

  
  <div class="section">
    <h2>📋 数据说明</h2>
    <table>
      <tr><th>项目</th><th>说明</th></tr>
      <tr><td>数据源</td><td>[库名.表名]（[分区/全量说明]）</td></tr>
      <tr><td>时间范围</td><td>[起始] ~ [结束]（按 [时间字段] 过滤）</td></tr>
      <tr><td>{{METRIC_1}}</td><td>[公式]</td></tr>
    </table>
  </div>

  
  <div class="section">
    <h2>📊 一、{{SECTION_1_TITLE}}</h2>
    <div class="chart-row">
      <div class="chart-box">
        <h3>{{CHART_1_TITLE}}</h3>
        <div class="chart-container"><canvas id="chart_{{id1}}"></canvas></div>
      </div>
      <div class="chart-box">
        <h3>{{CHART_2_TITLE}}</h3>
        <div class="chart-container"><canvas id="chart_{{id2}}"></canvas></div>
      </div>
    </div>
    <table>
      <thead><tr><th>{{COL_1}}</th><th>{{COL_2}}</th><th>{{COL_3}}</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  
  <div class="section">
    <h2>🛠️ {{ACTION_TYPE}}建议</h2>
    <table class="suggestion-table">
      <thead><tr><th>优先级</th><th>{{ACTION_TYPE}}</th><th>数据依据</th><th>预期效果</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  
  <div class="section">
    <h2>📌 我将自行核实的下一步</h2>
    <table><tr><th>待核实项</th><th>原因</th><th>动作</th></tr></table>
  </div>

  
  <div class="section" style="background: linear-gradient(135deg, #e8f0fd 0%, #f0f4ff 100%); border-left: 4px solid #3498db;">
    <h2>🔒 本次使用的固化查询</h2>
    <table>
      <tr><th>查询名称</th><th>验证日期</th></tr>
      <tr><td>{{FQ_NAME}}</td><td>{{VERIFY_DATE}}</td></tr>
    </table>
    <p style="margin-top: 12px; color: #555; font-size: 13px;">
      💡 以上查询使用的是已固化的分析逻辑。如果业务规则发生变化或分析逻辑需要调整，可以告诉我"更新 XX 查询"，我会重新验证并更新。
    </p>
  </div>

  
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

### {{SCENARIO_1}} → 环形图 (Doughnut)

```javascript
renderChart('chart_{{id}}', {
  type: 'doughnut',
  data: {
    labels: [{{LABELS}}],
    datasets: [{
      data: [{{DATA}}],
      backgroundColor: ['#3498db', '#e74c3c', '#f39c12', '#95a5a6']
    }]
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

### {{SCENARIO_2}} → 水平柱状图 (Bar, indexAxis: 'y')

```javascript
renderChart('chart_{{id}}', {
  type: 'bar',
  data: {
    labels: [{{LABELS}}],
    datasets: [{
      label: '{{MEASURE}}',
      data: [{{DATA}}],
      backgroundColor: ['#e74c3c', '#3498db', '#f39c12', '#95a5a6', '#2ecc71', '#9b59b6']
    }]
  },
  options: { indexAxis: 'y', plugins: { legend: { display: false } } }
});
```

### 两维度交叉 → 堆叠柱状图

```javascript
renderChart('chart_{{id}}', {
  type: 'bar',
  data: {
    labels: [{{DIM_A_VALUES}}],
    datasets: [
      { label: '{{DIM_B_1}}', data: [{{DATA_1}}], backgroundColor: '#e74c3c' },
      { label: '{{DIM_B_2}}', data: [{{DATA_2}}], backgroundColor: '#3498db' }
    ]
  },
  options: { scales: { x: { stacked: true }, y: { stacked: true } } }
});
```

### 趋势分析 → 折线图 (Line)

```javascript
renderChart('chart_{{id}}', {
  type: 'line',
  data: {
    labels: [{{TIME_LABELS}}],
    datasets: [
      { label: '{{SERIES_1}}', data: [{{DATA_1}}], borderColor: '#e74c3c', tension: 0.3 },
      { label: '{{SERIES_2}}', data: [{{DATA_2}}], borderColor: '#3498db', tension: 0.3 }
    ]
  }
});
```

## 五、图表选型速查

| 分析场景     | 图表类型        | Chart.js type           | 适用条件         |
| -------- | ----------- | ----------------------- | ------------ |
| 占比分布     | 环形图         | `doughnut`              | 分类 ≤ 6 个     |
| Top N 排行 | 水平柱状图       | `bar` + `indexAxis:'y'` | Top N 排行     |
| 两维度交叉    | 堆叠柱状图       | `bar` + `stacked`       | 两维度交叉对比      |
| 时间趋势     | 折线图         | `line`                  | 时间序列 ≥ 5 个周期 |
| 前后对比     | 分组柱状图       | `bar` (grouped)         | 两期对比         |
| 漏斗转化     | KPI 卡片 + 折线 | `kpi-card` + `line`     | 多步骤转化率       |

## 六、配色方案

| 用途     | 颜色   | 色值                    |
| ------ | ---- | --------------------- |
| 负面/主问题 | 红    | `#e74c3c`             |
| 中性偏负   | 蓝    | `#3498db`             |
| 正常/正面  | 绿    | `#27ae60`             |
| 警告/中等  | 橙    | `#f39c12`             |
| 其他/次要  | 灰    | `#95a5a6`             |
| 辅助     | 紫    | `#9b59b6`             |
| 主题色    | 渐变蓝紫 | `#667eea` → `#764ba2` |

## 七、表述铁律

| 禁止        | 替代                             |
| --------- | ------------------------------ |
| "优化一下 XX" | 具体到"XX 维度 XX 指标 XX%，建议 XX 动作"  |
| "提升体验"    | 具体到"XX 端 XX 指标月环比 +X%，建议排查 XX" |
| "可能需要调整"  | 具体到"建议将 XX 的 XX 数据调整 XX"       |
| "数据不够"    | "当前数据仅覆盖 N 天，样本量 M 单，结论仅供参考"   |

## 八、建议表格中的优先级标签

| 优先级 | 样式                                          | 含义       |
| --- | ------------------------------------------- | -------- |
| P0  | `<span class="badge badge-red">P0</span>`   | 紧急，需立即处理 |
| P1  | `<span class="badge badge-blue">P1</span>`  | 重要，本周内处理 |
| P2  | `<span class="badge badge-green">P2</span>` | 改善项，排期处理 |

## 九、报告重建铁律

1. **每次全量重建**：报告数据必须全部来自当次查询结果。禁止在旧报告文件上修改数字——KPI 卡片、图表、表格三处数据必须一致。
2. **canvas 与 renderChart 配对**：HTML 中每个 `<canvas id="chart_xx">` 都必须有对应的 `renderChart('chart_xx', {...})` 调用。未使用的图表要同时移除 canvas 和 JS 调用。
3. **时间范围用 `date` 命令确认**：生成报告前用 `date` 命令获取当前日期，"近一周" = 今天减 7 天到昨天（T-1）。
