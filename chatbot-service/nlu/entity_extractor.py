"""实体抽取 —— 从用户输入中提取结构化信息（日期、人名、产品名等）。"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Entity:
    """抽取到的实体。"""

    name: str
    type: str  # date / person / product / location / number ...
    value: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0


class EntityExtractor:
    """实体抽取器，支持 regex 规则 + LLM 两种方式。"""

    # 内置正则规则
    PATTERNS: list[tuple[str, str]] = [
        (r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "date"),
        (r"\d{1,2}月\d{1,2}[日号]", "date"),
        (r"1[3-9]\d{9}", "phone"),
        (r"\d{18}|\d{17}[Xx]", "id_number"),
        (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "email"),
    ]

    def __init__(self) -> None:
        import re

        self._compiled = [(re.compile(p), t) for p, t in self.PATTERNS]

    def extract_by_rule(self, text: str) -> list[Entity]:
        """基于正则的实体抽取。"""
        entities: list[Entity] = []
        seen: set[tuple[int, int]] = set()

        for pattern, entity_type in self._compiled:
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span not in seen:
                    seen.add(span)
                    entities.append(Entity(
                        name=entity_type,
                        type=entity_type,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                    ))
        return entities

    async def extract_by_llm(self, text: str) -> list[Entity]:
        """使用 LLM 进行实体抽取（适合复杂或非标准实体）。"""
        from config.settings import get_settings

        settings = get_settings()

        import openai

        client = openai.AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

        prompt = (
            "从以下文本中提取实体，返回 JSON 数组。\n"
            '每个实体格式: {"name": "实体名", "type": "类型(date/person/product/location/organization)", "value": "原文值"}\n\n'
            f'文本: """{text}"""\n\n'
            "只返回 JSON 数组，不要其他内容。"
        )

        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=512,
        )

        import json

        raw = response.choices[0].message.content or "[]"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []

        return [
            Entity(
                name=item.get("name", ""),
                type=item.get("type", "unknown"),
                value=item.get("value", ""),
            )
            for item in data
            if isinstance(item, dict)
        ]

    async def extract(self, text: str, use_llm: bool = False) -> list[Entity]:
        """统一入口：先规则抽取，可选 LLM 补充。"""
        entities = self.extract_by_rule(text)
        if use_llm:
            llm_entities = await self.extract_by_llm(text)
            entities.extend(llm_entities)
        return entities
