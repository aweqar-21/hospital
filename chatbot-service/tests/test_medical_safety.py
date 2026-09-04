"""医疗咨询安全规则测试。"""

import pytest

from core.context_builder import SYSTEM_PROMPT
from core.medical_safety import emergency_reply, is_emergency


@pytest.mark.parametrize(
    "message",
    [
        "突然胸痛而且呼吸困难",
        "我不想活了",
        "我喘不过气，嘴唇发紫",
        "我刚刚吞了农药",
        "伤口流血不止",
        "刚才晕厥了",
        "胸痛无法忍受",
        "胸痛无缓解",
        "持续无缓解的胸痛",
        "没有咳嗽，胸痛越来越严重",
        "我想死",
        "我现在想死",
        "真的想死",
        "大量出血止不住",
        "我吃了一瓶安眠药",
        "医生问有没有胸痛，我说没有停过",
        "医生问有没有胸痛，我说没有缓解",
        "出现胸痛",
        "出现呼吸困难",
        "我喘不上气",
        "患者意识不清",
        "病人昏迷",
        "发生大出血",
        "全身抽搐",
        "疑似服毒",
        "有自杀念头",
        "存在自伤行为",
    ],
)
def test_detects_explicit_emergency_messages(message):
    assert is_emergency(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "",
        "轻微感冒应该挂什么科",
        "我没有胸痛，只是咳嗽",
        "医生问有没有呼吸困难，我说没有",
        "否认胸痛",
        "我不会伤害自己",
        "我不想死",
    ],
)
def test_does_not_classify_negated_or_routine_messages_as_emergency(message):
    assert is_emergency(message) is False


@pytest.mark.parametrize(
    "message",
    [
        "没有胸痛但呼吸困难",
        "没有胸痛但是呼吸困难",
        "没有胸痛但抽搐",
        "否认胸痛却喘不上气",
    ],
)
def test_detects_positive_symptom_after_contrast_with_negated_symptom(message):
    assert is_emergency(message) is True


def test_emergency_reply_directs_user_to_immediate_emergency_care():
    reply = emergency_reply()
    assert "立即" in reply
    assert "急诊" in reply
    assert "不要等待" in reply
    assert "不要自行驾车" in reply
    assert "身边的人陪同" in reply


def test_system_prompt_requires_medical_limits_and_department_advice():
    assert "不能替代医生" in SYSTEM_PROMPT
    assert "不得作出确定性诊断" in SYSTEM_PROMPT
    assert "开具处方" in SYSTEM_PROMPT
    assert "简洁概括" in SYSTEM_PROMPT
    assert "可能的原因" in SYSTEM_PROMPT
    assert "建议科室" in SYSTEM_PROMPT
    assert "就医紧急程度" in SYSTEM_PROMPT
    assert "下一步建议" in SYSTEM_PROMPT
    assert "急救服务" in SYSTEM_PROMPT
