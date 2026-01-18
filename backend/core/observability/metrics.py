"""
Metrics collection for JARVISv4
Implements a Prometheus-compatible metrics collector.
"""
from datetime import datetime, UTC
from typing import Dict, Optional
from pydantic import BaseModel, Field

class MetricsCollector(BaseModel):
    """Collects and stores metrics for the system (Prometheus-compatible)"""
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Performance metrics
    total_tokens_used: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0

    # Node metrics
    nodes_executed: int = 0
    nodes_succeeded: int = 0
    nodes_failed: int = 0

    # Model metrics
    model_inference_count: int = 0
    model_inference_total_time: float = 0.0
    model_average_inference_time: float = 0.0

    # Error metrics
    error_counts: Dict[str, int] = {}

    # Resource metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # System metrics
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def increment_requests(self, success: bool = True, tokens_used: int = 0, execution_time: float = 0.0):
        """Increment request counters"""
        self.total_requests += 1
        self.last_updated = datetime.now(UTC)

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.total_tokens_used += tokens_used
        self.total_execution_time += execution_time

        if self.total_requests > 0:
            self.average_execution_time = self.total_execution_time / self.total_requests

    def increment_nodes(self, success: bool = True):
        """Increment node execution counters"""
        self.nodes_executed += 1
        self.last_updated = datetime.now(UTC)

        if success:
            self.nodes_succeeded += 1
        else:
            self.nodes_failed += 1

    def record_model_inference(self, duration: float):
        """Record model inference metrics"""
        self.model_inference_count += 1
        self.model_inference_total_time += duration
        self.model_average_inference_time = self.model_inference_total_time / self.model_inference_count
        self.last_updated = datetime.now(UTC)

    def record_error(self, error_type: str):
        """Record error occurrence"""
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        self.last_updated = datetime.now(UTC)

    def update_resource_usage(self, memory_mb: Optional[float] = None, cpu_percent: Optional[float] = None):
        """Update resource usage metrics"""
        if memory_mb is not None:
            self.memory_usage_mb = memory_mb
        if cpu_percent is not None:
            self.cpu_usage_percent = cpu_percent
        self.last_updated = datetime.now(UTC)

    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus-compatible metrics output"""
        lines = [
            "# HELP jarvis_requests_total Total number of requests processed",
            "# TYPE jarvis_requests_total counter",
            f"jarvis_requests_total {self.total_requests}",
            "",
            "# HELP jarvis_requests_success_total Number of successful requests",
            "# TYPE jarvis_requests_success_total counter",
            f"jarvis_requests_success_total {self.successful_requests}",
            "",
            "# HELP jarvis_requests_failed_total Number of failed requests",
            "# TYPE jarvis_requests_failed_total counter",
            f"jarvis_requests_failed_total {self.failed_requests}",
            "",
            "# HELP jarvis_tokens_used_total Total tokens used",
            "# TYPE jarvis_tokens_used_total counter",
            f"jarvis_tokens_used_total {self.total_tokens_used}",
            "",
            "# HELP jarvis_execution_time_total Total execution time in seconds",
            "# TYPE jarvis_execution_time_total counter",
            f"jarvis_execution_time_total {self.total_execution_time}",
            "",
            "# HELP jarvis_execution_time_average Average execution time in seconds",
            "# TYPE jarvis_execution_time_average gauge",
            f"jarvis_execution_time_average {self.average_execution_time}",
            "",
            "# HELP jarvis_nodes_executed_total Total nodes executed",
            "# TYPE jarvis_nodes_executed_total counter",
            f"jarvis_nodes_executed_total {self.nodes_executed}",
            "",
            "# HELP jarvis_model_inference_total Total model inferences",
            "# TYPE jarvis_model_inference_total counter",
            f"jarvis_model_inference_total {self.model_inference_count}",
            "",
            "# HELP jarvis_memory_usage_mb Current memory usage in MB",
            "# TYPE jarvis_memory_usage_mb gauge",
            f"jarvis_memory_usage_mb {self.memory_usage_mb}",
            "",
            "# HELP jarvis_cpu_usage_percent Current CPU usage percentage",
            "# TYPE jarvis_cpu_usage_percent gauge",
            f"jarvis_cpu_usage_percent {self.cpu_usage_percent}",
        ]

        # Add error metrics
        for error_type, count in self.error_counts.items():
            lines.extend([
                "",
                f"# HELP jarvis_errors_total_{error_type} Total {error_type} errors",
                f"# TYPE jarvis_errors_total_{error_type} counter",
                f"jarvis_errors_total_{error_type} {count}"
            ])

        return "\n".join(lines)
