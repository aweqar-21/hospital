"""监控指标收集 —— 记录延迟、置信度分布、请求量等。"""
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricPoint:
    """单次指标记录。"""

    name: str
    value: float
    labels: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """简易的指标收集器（生产环境建议使用 Prometheus / OpenTelemetry）。"""

    def __init__(self) -> None:
        self._metrics: defaultdict[str, list[MetricPoint]] = defaultdict(list)
        self._counters: defaultdict[str, int] = defaultdict(int)

    def record(self, name: str, value: float, labels: dict | None = None) -> None:
        """记录一个指标点。"""
        self._metrics[name].append(
            MetricPoint(name=name, value=value, labels=labels or {})
        )

    def increment(self, name: str, delta: int = 1) -> None:
        """累加计数器。"""
        self._counters[name] += delta

    def get_counter(self, name: str) -> int:
        """获取计数器值。"""
        return self._counters.get(name, 0)

    def get_stats(self, name: str) -> dict:
        """获取指定指标的统计信息。"""
        points = self._metrics.get(name, [])
        if not points:
            return {}
        values = [p.value for p in points]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }

    def latency_context(self, name: str, labels: dict | None = None):
        """上下文管理器 —— 自动记录耗时。"""

        class _LatencyCtx:
            def __init__(self2, collector, metric_name, metric_labels):
                self2.collector = collector
                self2.name = metric_name
                self2.labels = metric_labels or {}

            def __enter__(self2):
                self2.start = time.time()
                return self2

            def __exit__(self2, *args):
                elapsed = time.time() - self2.start
                self2.collector.record(self2.name, elapsed, self2.labels)

        return _LatencyCtx(self, name, labels)
