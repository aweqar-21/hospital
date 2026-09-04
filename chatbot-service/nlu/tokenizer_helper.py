"""中文分词辅助 —— 封装 jieba，支持自定义词典。"""
from typing import Optional


class TokenizerHelper:
    """中文分词与关键词提取工具。"""

    def __init__(self, user_dict_path: Optional[str] = None) -> None:
        import jieba

        self._jieba = jieba
        # 设置静默模式
        self._jieba.setLogLevel(20)

        if user_dict_path:
            self._jieba.load_userdict(user_dict_path)

    def add_words(self, words: list[str]) -> None:
        """动态添加自定义词。"""
        for w in words:
            self._jieba.add_word(w)

    def segment(self, text: str, mode: str = "exact") -> list[str]:
        """分词。
        - exact: 精确模式
        - full: 全模式
        - search: 搜索引擎模式
        """
        if mode == "full":
            return list(self._jieba.cut(text, cut_all=True))
        elif mode == "search":
            return list(self._jieba.cut_for_search(text))
        return list(self._jieba.cut(text, cut_all=False))

    def extract_keywords(self, text: str, top_k: int = 5) -> list[tuple[str, float]]:
        """提取关键词（TF-IDF 算法）。"""
        import jieba.analyse

        return jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)

    def extract_keywords_textrank(self, text: str, top_k: int = 5) -> list[tuple[str, float]]:
        """提取关键词（TextRank 算法）。"""
        import jieba.analyse

        return jieba.analyse.textrank(text, topK=top_k, withWeight=True)
