#!/usr/bin/env bash
# validate.sh — 数据分析技能结构完整性自动校验脚本。
# 用法：bash validate.sh [技能目录]
#   默认校验当前目录。
# 退出码：0 = 全部通过，1 = 存在错误，2 = 仅有警告。
set -euo pipefail

SKILL_DIR="${1:-.}"
ERRORS=0
WARNINGS=0

pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; ERRORS=$((ERRORS + 1)); }
warn() { echo "  ⚠️  $1"; WARNINGS=$((WARNINGS + 1)); }

echo "🔍 校验技能目录: $SKILL_DIR"
echo ""

# ── 1. 文件结构检查 ──────────────────────────────────────────────
echo "── 文件结构 ──"

for f in SKILL.md resources/warehouse_schema.md resources/metrics_definitions.md \
         resources/attribution_logic.md resources/output_standards.md; do
  if [[ -f "$SKILL_DIR/$f" ]]; then
    pass "$f 存在"
  else
    fail "$f 缺失"
  fi
done

echo ""

# ── 2. SKILL.md frontmatter 检查 ─────────────────────────────────
echo "── SKILL.md frontmatter ──"

if head -5 "$SKILL_DIR/SKILL.md" | grep -q '^name:'; then
  pass "frontmatter 含 name"
else
  fail "frontmatter 缺少 name"
fi

if head -5 "$SKILL_DIR/SKILL.md" | grep -q '^description:'; then
  pass "frontmatter 含 description"
else
  fail "frontmatter 缺少 description"
fi

if head -5 "$SKILL_DIR/SKILL.md" | grep -q '^version:'; then
  pass "frontmatter 含 version"
else
  fail "frontmatter 缺少 version"
fi

echo ""

# ── 3. 占位符残留检查 ────────────────────────────────────────────
echo "── 占位符残留 ──"

PLACEHOLDER_FILES=""
for f in SKILL.md resources/warehouse_schema.md resources/metrics_definitions.md \
         resources/attribution_logic.md resources/output_standards.md; do
  if [[ -f "$SKILL_DIR/$f" ]]; then
    COUNT=$(grep -c '{{[A-Z_]*}}' "$SKILL_DIR/$f" 2>/dev/null || true)
    if [[ "$COUNT" -gt 0 ]]; then
      PLACEHOLDER_FILES="$PLACEHOLDER_FILES $f($COUNT)"
    fi
  fi
done

if [[ -z "$PLACEHOLDER_FILES" ]]; then
  pass "无 {{占位符}} 残留"
else
  fail "以下文件仍有未替换的占位符:$PLACEHOLDER_FILES"
fi

echo ""

# ── 4. L2 原子方法数量检查 ───────────────────────────────────────
echo "── L2 原子方法 ──"

if [[ -f "$SKILL_DIR/resources/attribution_logic.md" ]]; then
  MTD_COUNT=$(grep -cE '^### MTD-[0-9]+' "$SKILL_DIR/resources/attribution_logic.md" 2>/dev/null || true)
  if [[ "$MTD_COUNT" -ge 8 ]]; then
    pass "L2 通用方法 ≥ 8 个（实际 $MTD_COUNT 个）"
  elif [[ "$MTD_COUNT" -ge 7 ]]; then
    warn "L2 通用方法仅 $MTD_COUNT 个（建议 ≥ 8，含 MTD-08 漏斗转化率）"
  else
    fail "L2 通用方法仅 $MTD_COUNT 个（要求 ≥ 8）"
  fi

  # 检查 8 要素覆盖度（抽样检查第一个非模板方法）
  FIRST_MTD_LINE=$(grep -nE '^### MTD-' "$SKILL_DIR/resources/attribution_logic.md" | head -1 | cut -d: -f1)
  if [[ -n "$FIRST_MTD_LINE" ]]; then
    NEXT_MTD_LINE=$(grep -nE '^### MTD-|^## L3' "$SKILL_DIR/resources/attribution_logic.md" | awk -v start="$FIRST_MTD_LINE" '$1 > start {print $1; exit}' | cut -d: -f1)
    if [[ -z "$NEXT_MTD_LINE" ]]; then
      NEXT_MTD_LINE=$(wc -l < "$SKILL_DIR/resources/attribution_logic.md")
    fi
    METHOD_BLOCK=$(sed -n "${FIRST_MTD_LINE},${NEXT_MTD_LINE}p" "$SKILL_DIR/resources/attribution_logic.md")

    ELEMENTS_OK=0
    for elem in "触发" "适用表" "参数" "步骤" "伪 SQL" "输出" "陷阱" "特别提示"; do
      if echo "$METHOD_BLOCK" | grep -q "\*\*${elem}"; then
        ELEMENTS_OK=$((ELEMENTS_OK + 1))
      fi
    done

    if [[ "$ELEMENTS_OK" -ge 7 ]]; then
      pass "L2 方法 8 要素覆盖度良好（$ELEMENTS_OK/8）"
    elif [[ "$ELEMENTS_OK" -ge 5 ]]; then
      warn "L2 方法 8 要素覆盖度不足（$ELEMENTS_OK/8），复杂方法应写全"
    else
      fail "L2 方法 8 要素严重缺失（$ELEMENTS_OK/8）"
    fi
  fi
else
  fail "attribution_logic.md 缺失，无法检查 L2"
fi

echo ""

# ── 5. L3 场景配置检查 ──────────────────────────────────────────
echo "── L3 场景配置 ──"

if [[ -f "$SKILL_DIR/resources/attribution_logic.md" ]]; then
  # 检查 L3 表格是否有 9 列（通过表头中的 | 数量判断）
  L3_HEADER=$(sed -n '/^## L3/,/^## L4/p' "$SKILL_DIR/resources/attribution_logic.md" | grep -E '^\|.*场景.*ID' | head -1 || true)
  if [[ -n "$L3_HEADER" ]]; then
    COL_COUNT=$(echo "$L3_HEADER" | tr -cd '|' | wc -c)
    # 9 列表头有 10 个 |（含首尾）
    if [[ "$COL_COUNT" -ge 10 ]]; then
      pass "L3 场景表包含 9 列"
    else
      fail "L3 场景表仅 $((COL_COUNT - 1)) 列（要求 9 列：ID/名称/触发词/方法链/维度/指标/必需输入/固化查询/备注）"
    fi
  else
    warn "未找到 L3 场景配置表头"
  fi

  # 检查场景数量
  SCENE_COUNT=$(sed -n '/^## L3/,/^## L4/p' "$SKILL_DIR/resources/attribution_logic.md" | grep -cE '^\| S[0-9]' 2>/dev/null || true)
  if [[ "$SCENE_COUNT" -ge 1 ]]; then
    pass "L3 配置了 $SCENE_COUNT 个场景"
  else
    fail "L3 未配置任何场景"
  fi
fi

echo ""

# ── 6. L4 决策树检查 ────────────────────────────────────────────
echo "── L4 决策树 ──"

if [[ -f "$SKILL_DIR/resources/attribution_logic.md" ]]; then
  if grep -q "前置校验" "$SKILL_DIR/resources/attribution_logic.md" && \
     grep -q "全局 Checklist" "$SKILL_DIR/resources/attribution_logic.md"; then
    pass "L4 包含前置校验和全局 Checklist"
  else
    fail "L4 缺少前置校验或全局 Checklist（应为 5 步线性路径）"
  fi
fi

echo ""

# ── 7. 资源文件链接有效性 ────────────────────────────────────────
echo "── 资源索引链接 ──"

if [[ -f "$SKILL_DIR/SKILL.md" ]]; then
  # 必选资源文件
  for target in "resources/metrics_definitions.md" "resources/warehouse_schema.md" \
                "resources/attribution_logic.md" "resources/output_standards.md"; do
    if grep -q "$target" "$SKILL_DIR/SKILL.md"; then
      if [[ -f "$SKILL_DIR/$target" ]]; then
        pass "SKILL.md 引用 $target → 文件存在"
      else
        fail "SKILL.md 引用 $target → 文件不存在"
      fi
    else
      warn "SKILL.md 未引用 $target"
    fi
  done

  # 可选资源文件（fixed_queries.md）：引用了但文件不存在才报错，未引用则跳过
  if grep -q "resources/fixed_queries.md" "$SKILL_DIR/SKILL.md"; then
    if [[ -f "$SKILL_DIR/resources/fixed_queries.md" ]]; then
      pass "SKILL.md 引用 resources/fixed_queries.md → 文件存在"
    else
      fail "SKILL.md 引用 resources/fixed_queries.md → 文件不存在"
    fi
  else
    pass "fixed_queries.md 未引用（可选，正常）"
  fi
fi

echo ""

# ── 8. odps-query 引用检查 ──────────────────────────────────────
echo "── 查询执行 ──"

if [[ -f "$SKILL_DIR/SKILL.md" ]]; then
  if grep -q "odps-query" "$SKILL_DIR/SKILL.md"; then
    pass "SKILL.md 引用了 odps-query 技能"
  else
    fail "SKILL.md 未引用 odps-query 技能"
  fi

  # 检查是否硬编码了具体路径
  if grep -qE '\.qoderworkcn|/skills/odps-query/scripts/' "$SKILL_DIR/SKILL.md"; then
    warn "SKILL.md 中硬编码了 odps-query 内部路径，建议改为技能名引用"
  else
    pass "未硬编码 odps-query 内部路径"
  fi
fi

echo ""

# ── 9. output_standards.md 基本检查 ─────────────────────────────
echo "── 输出层标准 ──"

if [[ -f "$SKILL_DIR/resources/output_standards.md" ]]; then
  for keyword in "renderChart" "Chart.js" "CSS" "表述铁律"; do
    if grep -q "$keyword" "$SKILL_DIR/resources/output_standards.md"; then
      pass "output_standards.md 含 $keyword"
    else
      warn "output_standards.md 缺少 $keyword"
    fi
  done
fi

echo ""

# ── 10. 口径唯一性检查 ──────────────────────────────────────────
echo "── 口径唯一性 ──"

if [[ -f "$SKILL_DIR/resources/metrics_definitions.md" ]] && [[ -f "$SKILL_DIR/SKILL.md" ]]; then
  # 提取 metrics_definitions.md 中的指标 ID
  METRIC_IDS=$(grep -oE 'M_[A-Z0-9_]+' "$SKILL_DIR/resources/metrics_definitions.md" 2>/dev/null | sort -u || true)
  if [[ -n "$METRIC_IDS" ]]; then
    DUPLICATE_FOUND=false
    for mid in $METRIC_IDS; do
      # 检查 SKILL.md 中是否也定义了该指标（而非仅引用）
      if grep -qE "$mid.*公式|$mid.*=" "$SKILL_DIR/SKILL.md" 2>/dev/null; then
        warn "指标 $mid 可能在 SKILL.md 中重复定义（应仅在 metrics_definitions.md 定义）"
        DUPLICATE_FOUND=true
      fi
    done
    if [[ "$DUPLICATE_FOUND" == false ]]; then
      pass "未发现指标口径重复定义"
    fi
  else
    warn "metrics_definitions.md 中未找到 M_XX 格式的指标 ID"
  fi
fi

echo ""

# ── 11. 固化查询检查（可选） ──────────────────────────────────────
echo "── 固化查询 ──"

if [[ -f "$SKILL_DIR/resources/fixed_queries.md" ]]; then
  # 检查是否有至少一个 FQ-XX 节
  FQ_COUNT=$(grep -cE '^## FQ-[0-9]+' "$SKILL_DIR/resources/fixed_queries.md" 2>/dev/null || true)
  if [[ "$FQ_COUNT" -ge 1 ]]; then
    pass "fixed_queries.md 含 $FQ_COUNT 个固化查询"
  else
    warn "fixed_queries.md 存在但未找到 FQ-XX 节"
  fi

  # 检查验证日期
  VERIFY_COUNT=$(grep -cE '^\- \*\*验证日期' "$SKILL_DIR/resources/fixed_queries.md" 2>/dev/null || true)
  if [[ "$VERIFY_COUNT" -ge "$FQ_COUNT" ]] && [[ "$FQ_COUNT" -ge 1 ]]; then
    pass "所有固化查询均含验证日期"
  elif [[ "$FQ_COUNT" -ge 1 ]]; then
    fail "部分固化查询缺少验证日期（$VERIFY_COUNT/$FQ_COUNT）"
  fi

  # 检查场景名称
  NAME_COUNT=$(grep -cE '^\- \*\*场景名称' "$SKILL_DIR/resources/fixed_queries.md" 2>/dev/null || true)
  if [[ "$NAME_COUNT" -ge "$FQ_COUNT" ]] && [[ "$FQ_COUNT" -ge 1 ]]; then
    pass "所有固化查询均含场景名称"
  elif [[ "$FQ_COUNT" -ge 1 ]]; then
    warn "部分固化查询缺少场景名称（$NAME_COUNT/$FQ_COUNT）"
  fi

  # 检查参数占位符风格
  if grep -qE '\$\{[a-z_]+\}' "$SKILL_DIR/resources/fixed_queries.md"; then
    pass "固化查询使用 \${param} 参数风格"
  elif [[ "$FQ_COUNT" -ge 1 ]]; then
    warn "固化查询中未检测到 \${param} 风格的参数占位符"
  fi

  # 检查 L3 场景表中是否有对应的 FQ 引用
  if [[ -f "$SKILL_DIR/resources/attribution_logic.md" ]]; then
    L3_FQ_REFS=$(sed -n '/^## L3/,/^## L4/p' "$SKILL_DIR/resources/attribution_logic.md" | grep -oE 'FQ-[0-9]+' 2>/dev/null | sort -u || true)
    FIXED_FQS=$(grep -oE 'FQ-[0-9]+' "$SKILL_DIR/resources/fixed_queries.md" 2>/dev/null | sort -u || true)
    if [[ -n "$L3_FQ_REFS" ]]; then
      ORPHAN=false
      for ref in $L3_FQ_REFS; do
        if ! echo "$FIXED_FQS" | grep -q "$ref"; then
          warn "L3 场景引用了 $ref，但 fixed_queries.md 中未找到对应定义"
          ORPHAN=true
        fi
      done
      if [[ "$ORPHAN" == false ]]; then
        pass "L3 场景中的固化查询引用均有对应定义"
      fi
    else
      pass "L3 场景中暂无固化查询引用（正常，新技能可后续添加）"
    fi
  fi
else
  pass "fixed_queries.md 未创建（可选，已验证场景可后续添加）"
fi

echo ""

# ── 汇总 ────────────────────────────────────────────────────────
echo "═══════════════════════════════════════"
if [[ "$ERRORS" -eq 0 ]] && [[ "$WARNINGS" -eq 0 ]]; then
  echo "🎉 全部通过！"
  exit 0
elif [[ "$ERRORS" -eq 0 ]]; then
  echo "⚠️  通过（$WARNINGS 个警告）"
  exit 2
else
  echo "❌ 未通过：$ERRORS 个错误，$WARNINGS 个警告"
  exit 1
fi
