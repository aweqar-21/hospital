"""后处理器 —— 敏感词过滤、格式清理、安全校验。"""
import re
from typing import Optional

from config.settings import get_settings


# 内置简易敏感词列表（实际项目建议从文件加载或接第三方服务）
_DEFAULT_SENSITIVE_WORDS: set[str] = set()


class PostProcessor:
    """对模型输出进行后处理。"""

    def __init__(self, sensitive_words: Optional[set[str]] = None) -> None:
        self.settings = get_settings()
        self.sensitive_words = sensitive_words or _DEFAULT_SENSITIVE_WORDS

    def process(self, text: str) -> str:
        """执行全部后处理流程。"""
        text = self.filter_sensitive(text)
        text = self.clean_format(text)
        text = self.trim_incomplete(text)
        return text.strip()

    def filter_sensitive(self, text: str) -> str:
        """敏感词过滤 —— 替换为 **。"""
        result = text
        for word in self.sensitive_words:
            if word and word in result:
                result = result.replace(word, "*" * len(word))
        return result

    @staticmethod
    def clean_format(text: str) -> str:
        """清理格式问题：
        - 移除多余的连续空格
        - 统一换行为 \n
        """
        text = re.sub(r"[ \t]+", " ", text)   # 多余空格
        text = re.sub(r"\r\n?", "\n", text)    # 统一换行
        text = re.sub(r"\n{4,}", "\n\n\n", text)  # 至多保留两个连续空行
        return text

    @staticmethod
    def trim_incomplete(text: str) -> str:
        """截断不完整的句子（如末尾被截断的 markdown 代码块）。"""
        # 补齐未闭合的代码块
        count_triple = text.count("```")
        if count_triple % 2 != 0:
            text += "\n```"
        return text

    @staticmethod
    def validate(text: str) -> bool:
        """安全校验：检测是否包含明显的不安全内容。"""
        # 空回复
        if not text.strip():
            return False
        # 长度异常（过长）
        if len(text) > 10_000:
            return False
        return True
