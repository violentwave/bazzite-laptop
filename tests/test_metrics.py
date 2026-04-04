"""Unit tests for ai/metrics.py MetricsRecorder."""



from ai.metrics import (
    BUFFER_SIZE,
    FLUSH_INTERVAL_S,
    VALID_METRIC_TYPES,
)


class TestValidMetricTypes:
    def test_valid_types(self):
        assert "cache" in VALID_METRIC_TYPES
        assert "budget" in VALID_METRIC_TYPES
        assert "provider" in VALID_METRIC_TYPES
        assert "tool" in VALID_METRIC_TYPES
        assert "timer" in VALID_METRIC_TYPES


class TestBufferFlush:
    def test_buffer_size_constant(self):
        assert BUFFER_SIZE == 100

    def test_flush_interval_constant(self):
        assert FLUSH_INTERVAL_S == 60
