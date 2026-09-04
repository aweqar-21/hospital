"""文本预处理工具 —— emoji 过滤、敏感词检测、截断等。"""
import re
from typing import Optional


def clean_text(text: str) -> str:
    """基础文本清洗：
    - 去除控制字符（保留换行符）
    - 合并多余空白
    """
    # 移除控制字符（0x00-0x1F，但保留 \n 0x0A 和 \t 0x09）
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # 合并空格
    text = re.sub(r"[ \t]{2,}", " ", text)
    # 合并连续换行（保留至多 2 个）
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_sensitive(text: str, keywords: Optional[set[str]] = None) -> list[str]:
    """检测文本中的敏感词，返回匹配到的词列表。"""
    if keywords is None:
        keywords = set()
    found: list[str] = []
    for word in keywords:
        if word and word in text:
            found.append(word)
    return found


def truncate_text(text: str, max_chars: int = 4096, suffix: str = "...") -> str:
    """截断文本到指定字符数（按字符，非字节）。"""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def strip_emojis(text: str) -> str:
    """移除文本中的 emoji 表情符号。"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # 表情符号
        "\U0001F300-\U0001F5FF"  # 符号与象形
        "\U0001F680-\U0001F6FF"  # 交通与地图
        "\U0001F1E0-\U0001F1FF"  # 旗帜
        "\U00002702-\U000027B0"  # 杂项符号
        "\U000024C2-\U0001F251"  # 杂项符号和象形扩展
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def normalize_whitespace(text: str) -> str:
    """将中文/英文之间的空格规范化。"""
    # 中文与英文之间加空格
    text = re.sub(r"([一-鿿])([a-zA-Z])", r"\1 \2", text)
    text = re.sub(r"([a-zA-Z])([一-鿿])", r"\1 \2", text)
    return text
