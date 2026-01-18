import logging
from backend.core.observability import MetricsCollector, setup_observability

def test_metrics_collector_initialization():
    collector = MetricsCollector()
    assert collector.total_requests == 0
    assert collector.successful_requests == 0
    assert "jarvis_requests_total 0" in collector.get_prometheus_metrics()

def test_metrics_increment():
    collector = MetricsCollector()
    collector.increment_requests(success=True, tokens_used=50, execution_time=0.5)
    assert collector.total_requests == 1
    assert collector.successful_requests == 1
    assert collector.total_tokens_used == 50
    assert collector.average_execution_time == 0.5

def test_setup_observability():
    logger = setup_observability(log_level="DEBUG")
    assert logger.name == "JARVISv4"
    assert logger.level == logging.DEBUG
