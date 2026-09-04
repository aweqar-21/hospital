"""情感分析 —— 评估用户情绪，用于调整回复策略。"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SentimentResult:
    label: str  # positive / negative / neutral
    score: float  # 0.0 - 1.0


class SentimentAnalyzer:
    """情感分析器 —— 支持词典 / 模型 / LLM 三种方式。"""

    # 简易情感词典
    POSITIVE_WORDS = {"好", "棒", "赞", "开心", "喜欢", "感谢", "优秀", "完美"}
    NEGATIVE_WORDS = {"差", "烂", "生气", "讨厌", "失望", "垃圾", "糟糕", "不行"}

    def analyze_by_lexicon(self, text: str) -> SentimentResult:
        """基于情感词典的快速分析。"""
        pos = sum(1 for w in self.POSITIVE_WORDS if w in text)
        neg = sum(1 for w in self.NEGATIVE_WORDS if w in text)

        if pos > neg:
            return SentimentResult(label="positive", score=0.7)
        elif neg > pos:
            return SentimentResult(label="negative", score=0.7)
        return SentimentResult(label="neutral", score=0.5)

    async def analyze_by_llm(self, text: str) -> SentimentResult:
        """使用 LLM 进行情感分析。"""
        from config.settings import get_settings

        settings = get_settings()

        import openai

        client = openai.AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f'分析以下文本的情绪，返回JSON: {{"label": "positive/negative/neutral", "score": 0.0-1.0}}\n\n'
                        f'文本: """{text}"""'
                    ),
                }
            ],
            temperature=0.0,
            max_tokens=64,
        )

        import json

        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return SentimentResult(label="neutral", score=0.5)

        return SentimentResult(
            label=data.get("label", "neutral"),
            score=data.get("score", 0.5),
        )

    async def analyze(self, text: str, use_llm: bool = False) -> SentimentResult:
        """统一入口。"""
        result = self.analyze_by_lexicon(text)
        if result.label != "neutral" and not use_llm:
            return result
        if use_llm:
            return await self.analyze_by_llm(text)
        return result
