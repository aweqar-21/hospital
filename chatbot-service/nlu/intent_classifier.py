"""意图分类器 —— 支持规则匹配 / 轻量模型 / 大模型三种策略。"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from config.settings import get_settings


DEFAULT_INTENTS_PATH = Path(__file__).resolve().parents[1] / "config" / "intents.yaml"


@dataclass
class IntentResult:
    intent: str
    confidence: float
    description: str = ""


@dataclass
class IntentRule:
    name: str
    description: str
    examples: list[str] = field(default_factory=list)
    priority: int = 99


class IntentClassifier:
    """意图识别 —— 可插拔策略。"""

    def __init__(self, intents_yaml_path: str | Path = DEFAULT_INTENTS_PATH) -> None:
        self.settings = get_settings()
        self.rules: list[IntentRule] = self._load_rules(intents_yaml_path)

    # ---------- 规则匹配 ----------
    def classify_by_rule(self, text: str) -> Optional[IntentResult]:
        """基于关键词 / 示例的规则匹配。适合简单、高频意图。"""
        text_lower = text.lower()
        best: Optional[IntentResult] = None

        for rule in self.rules:
            for example in rule.examples:
                if example.lower() in text_lower:
                    confidence = 1.0 if text_lower == example.lower() else 0.85
                    if best is None or confidence > best.confidence:
                        best = IntentResult(
                            intent=rule.name,
                            confidence=confidence,
                            description=rule.description,
                        )
        return best

    # ---------- LLM 分类 ----------
    async def classify_by_llm(self, text: str) -> IntentResult:
        """使用大模型进行意图分类。"""
        import json
        import openai

        intent_names = [r.name for r in self.rules]
        if not intent_names:
            return IntentResult(intent="chitchat", confidence=0.3)

        # 检查 API Key
        api_key = self.settings.LLM_API_KEY
        if not api_key or api_key == "sk-your-api-key-here":
            return IntentResult(intent="chitchat", confidence=0.3)

        try:
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=self.settings.LLM_BASE_URL,
                timeout=15.0,
                max_retries=0,
            )
            prompt = (
                f"请将以下用户输入分类到以下意图之一：{intent_names}\n"
                f"意图说明：{ {r.name: r.description for r in self.rules} }\n\n"
                f'用户输入："{text}"\n\n'
                "请只返回 JSON 格式：{\"intent\": \"意图名\", \"confidence\": 0.0-1.0}"
            )
            response = await client.chat.completions.create(
                model=self.settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=128,
            )

            raw = response.choices[0].message.content or "{}"
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return IntentResult(intent="chitchat", confidence=0.3)

            return IntentResult(
                intent=data.get("intent", "chitchat"),
                confidence=data.get("confidence", 0.5),
            )
        except Exception:
            return IntentResult(intent="chitchat", confidence=0.3)

    # ---------- 统一入口 ----------
    async def classify(
        self, text: str, strategy: str = "auto"
    ) -> IntentResult:
        """自动选择策略：
        - "rule": 仅规则
        - "llm": 仅大模型
        - "auto": 先规则，置信度低时回退 LLM
        """
        if strategy in ("rule", "auto"):
            result = self.classify_by_rule(text)
            if result and result.confidence >= 0.8:
                return result

        if strategy in ("llm", "auto"):
            return await self.classify_by_llm(text)

        return IntentResult(intent="chitchat", confidence=0.3)

    # ---------- helpers ----------
    @staticmethod
    def _load_rules(path: str | Path) -> list[IntentRule]:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            return []
        rules: list[IntentRule] = []
        for item in data.get("intents", []):
            rules.append(IntentRule(
                name=item["name"],
                description=item.get("description", ""),
                examples=item.get("examples", []),
                priority=item.get("priority", 99),
            ))
        rules.sort(key=lambda r: r.priority)
        return rules
