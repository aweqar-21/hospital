"""评估脚本 —— 计算意图识别准确率、回复质量评分。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 示例测试集
TEST_CASES: list[dict] = [
    {"input": "你好", "expected_intent": "greet"},
    {"input": "再见", "expected_intent": "farewell"},
    {"input": "你能做什么", "expected_intent": "ask_capability"},
    {"input": "什么是 RAG", "expected_intent": "knowledge_qa"},
    {"input": "帮我查一下订单", "expected_intent": "task_query"},
]


async def evaluate_intent() -> dict:
    """评估意图识别准确率。"""
    from nlu.intent_classifier import IntentClassifier

    classifier = IntentClassifier()
    correct = 0
    total = len(TEST_CASES)
    details: list[dict] = []

    for case in TEST_CASES:
        result = await classifier.classify(case["input"], strategy="auto")
        is_correct = result.intent == case["expected_intent"]
        if is_correct:
            correct += 1
        details.append({
            "input": case["input"],
            "expected": case["expected_intent"],
            "predicted": result.intent,
            "confidence": result.confidence,
            "correct": is_correct,
        })

    accuracy = correct / total if total > 0 else 0
    return {"accuracy": accuracy, "total": total, "correct": correct, "details": details}


def main() -> None:
    import asyncio

    print("=" * 50)
    print("Chatbot 评估脚本")
    print("=" * 50)

    print("\n[意图识别评估]")
    result = asyncio.run(evaluate_intent())
    print(f"准确率: {result['accuracy']:.1%} ({result['correct']}/{result['total']})")
    for d in result["details"]:
        status = "✓" if d["correct"] else "✗"
        print(f"  {status} 「{d['input']}」→ {d['predicted']} (置信度: {d['confidence']:.0%})")

    print("\n评估完成。")


if __name__ == "__main__":
    main()
