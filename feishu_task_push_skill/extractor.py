"""
AI 任务提取器
- 使用 LLM 从消息文本中提取工作任务
- 支持 OpenAI 兼容 API（OpenAI / DeepSeek / 通义千问 / Moonshot 等）
- 未配置 API 时使用简单规则提取
"""

import json
import re
import requests


class TaskExtractor:
    """AI 任务提取器"""

    # 工作任务的关键词（命中越多越可能是任务）
    TASK_KEYWORDS = [
        "做", "搞", "处理", "完成", "实现", "搭建", "开发", "修改", "调整", "优化",
        "新增", "添加", "删除", "更新", "修复", "排查", "检查", "验证", "测试",
        "整理", "汇总", "统计", "分析", "调研", "设计", "编写", "录入", "导出",
        "对接", "联调", "部署", "上线", "发布", "配置", "设置", "创建",
        "任务", "需求", "指标", "报表", "看板", "数据", "接口", "功能", "模块",
        "文档", "报告", "周报", "月报", "方案", "计划", "流程", "逻辑",
        "宽表", "数据集", "模型", "脚本", "代码", "SQL", "API",
        "今天", "明天", "本周", "下周", "月底", "尽快", "优先", "紧急",
        "截止", "排期",
    ]

    # 非任务的特征
    NON_TASK_PATTERNS = [
        r"^(快干活|加油|哈哈|嘿嘿|嗯嗯|好的|收到|^ok$|^OK$)",
        r"^(笑死|太强了|牛逼|厉害|666)",
    ]

    def __init__(self, api_key="", base_url="https://api.openai.com/v1", model="gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_work_task(self, message_text):
        """判断消息是否是真正的工作任务（非闲聊）"""
        text = message_text.strip()
        # 去掉 @mention 部分
        text = re.sub(r"@\S+\s*", "", text).strip()

        if not text or len(text) < 4:
            return False

        # 检查非任务特征
        for pattern in self.NON_TASK_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return False

        # 计算任务关键词命中数
        score = sum(1 for kw in self.TASK_KEYWORDS if kw in text)

        # 有具体工作内容的特征
        has_work_content = (
            len(text) >= 8 and (
                score >= 1 or
                re.search(r"[\d]+[.、)]", text) or
                re.search(r"[：:]", text) or
                any(c in text for c in "？?！!。")
            )
        )

        return has_work_content

    def extract(self, message_text, sender_name=""):
        """从消息文本中提取任务列表，返回 [{"content": "..."}, ...]"""
        if self.api_key:
            return self._extract_with_ai(message_text, sender_name)
        else:
            return self._extract_simple(message_text, sender_name)

    # ==================== AI 提取 ====================

    def _extract_with_ai(self, message_text, sender_name=""):
        prompt = f"""请从以下飞书群消息中提取分配给接收人的工作任务。
消息发送者: {sender_name}
消息内容:
{message_text}

请以 JSON 数组格式返回提取的任务列表，每个任务包含 content 字段。
如果没有明确的工作任务，返回空数组 []。
只返回 JSON，不要其他文字。"""

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
                timeout=30,
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # 提取 JSON
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            tasks = json.loads(content)
            if isinstance(tasks, list):
                return [{"content": t.get("content", str(t))} if isinstance(t, dict) else {"content": str(t)}
                        for t in tasks]
            return []
        except Exception as e:
            print(f"  [AI 提取错误] {e}")
            return self._extract_simple(message_text, sender_name)

    # ==================== 规则提取（无 AI 回退） ====================

    def _extract_simple(self, message_text, sender_name=""):
        """简单规则提取：按行分割，过滤短行"""
        text = message_text.strip()
        if not text or len(text) < 5:
            return []

        lines = text.split("\n")
        tasks = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 去掉常见前缀
            cleaned = re.sub(r"^[\d]+[.、)）]\s*", "", line)
            cleaned = re.sub(r"^[-*•]\s*", "", cleaned)
            cleaned = re.sub(r"^(任务|待办|TODO|todo)[:：]\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            # 过滤太短的行
            if len(cleaned) >= 5:
                tasks.append({"content": cleaned})

        # 如果只有一整段文本且没有换行，整体作为一条任务
        if not tasks and len(text) >= 5:
            tasks.append({"content": text})

        return tasks
