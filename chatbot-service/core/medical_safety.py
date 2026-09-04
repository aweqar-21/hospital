"""医疗咨询中的紧急情况识别与分流提示。"""

EMERGENCY_CATEGORIES = {
    "心肺症状": ("胸痛", "呼吸困难", "喘不上气", "喘不过气", "嘴唇发紫"),
    "意识障碍": ("意识不清", "昏迷", "晕厥", "晕倒", "失去意识"),
    "严重出血": ("大出血", "流血不止", "出血不止", "大量出血", "大量出血止不住"),
    "抽搐": ("抽搐",),
    "中毒": ("服毒", "吞了农药", "喝了农药", "误服药物", "吃了一瓶安眠药"),
    "自杀风险": ("自杀", "不想活了", "想结束生命", "想死"),
    "自伤风险": ("自伤", "割腕", "伤害自己"),
}

EMERGENCY_TERMS = tuple(
    term for category_terms in EMERGENCY_CATEGORIES.values() for term in category_terms
)

_DIRECT_DENIAL_PREFIXES = ("没有", "无", "否认", "未见", "未出现", "不会")
_DIRECT_DENIAL_SUFFIXES = (
    "没有",
    "无",
    "否认",
    "未见",
    "未出现",
)
_CONTRAST_CONJUNCTIONS = ("但", "但是", "却")
_CLAUSE_BOUNDARIES = "，,。；;：:、！？!?\n"
_QUESTION_REPORT_DENIALS = ("我说没有", "表示没有", "回答没有")
_QUESTION_REPORT_DENIAL_NOUN_PHRASES = ("任何症状", "相关症状", "这些症状", "上述症状")
_TERM_SPECIFIC_DENIAL_PREFIXES = {"想死": ("不",)}


def _clause_start(message: str, position: int) -> int:
    """返回包含 position 的分句起始位置。"""
    return max(message.rfind(boundary, 0, position) for boundary in _CLAUSE_BOUNDARIES) + 1


def _clause_end(message: str, position: int) -> int:
    """返回包含 position 的分句结束位置。"""
    endings = [
        found for boundary in _CLAUSE_BOUNDARIES if (found := message.find(boundary, position)) != -1
    ]
    return min(endings, default=len(message))


def _has_direct_denial_prefix(text: str) -> bool:
    """仅识别紧邻症状的明确否认前缀。"""
    return any(
        text.endswith(prefix) and not (prefix == "没有" and text.endswith("有没有"))
        for prefix in _DIRECT_DENIAL_PREFIXES
    )


def _is_question_report_denial(
    message: str, start: int, end: int, before: str, term: str
) -> bool:
    """识别“医生问有没有症状，我说没有”这类问诊转述。"""
    following = message[end : end + 12].lstrip(_CLAUSE_BOUNDARIES)
    if "问有没有" not in before:
        return False

    for denial in _QUESTION_REPORT_DENIALS:
        if following.startswith(denial):
            remainder = following[len(denial) :]
            return (
                not remainder
                or remainder[0] in _CLAUSE_BOUNDARIES
                or remainder == term
                or remainder in _QUESTION_REPORT_DENIAL_NOUN_PHRASES
            )
    return False


def _is_negated(message: str, start: int, end: int, term: str) -> bool:
    """判断一个命中词附近是否被否定，而不影响消息中的其他命中词。"""
    before = message[_clause_start(message, start) : start]
    contrast_end = 0
    for conjunction in _CONTRAST_CONJUNCTIONS:
        position = before.rfind(conjunction)
        if position != -1:
            contrast_end = max(contrast_end, position + len(conjunction))
    before = before[contrast_end:]
    after = message[end : _clause_end(message, end)]
    term_specific_prefixes = _TERM_SPECIFIC_DENIAL_PREFIXES.get(term, ())
    return (
        _has_direct_denial_prefix(before)
        or before.endswith(term_specific_prefixes)
        or after in _DIRECT_DENIAL_SUFFIXES
        or _is_question_report_denial(message, start, end, before, term)
    )


def is_emergency(message: str) -> bool:
    """当用户消息包含预定义的紧急风险信号时返回 True。"""
    for term in EMERGENCY_TERMS:
        start = message.find(term)
        while start != -1:
            if not _is_negated(message, start, start + len(term), term):
                return True
            start = message.find(term, start + len(term))
    return False


def emergency_reply() -> str:
    """返回不延误治疗的紧急就医指引。"""
    return (
        "这可能是紧急医疗情况，请立即拨打当地急救电话或前往最近的急诊。"
        "请不要等待症状自行缓解，也不要自行驾车；请让身边的人陪同并协助就医。"
    )
