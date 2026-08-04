import logging
import sys

from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram

REQUEST_COUNTER = Counter("api_requests_total", "Total de requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("api_request_seconds", "Latência das requests", ["method", "path"])
ANALYSIS_COUNTER = Counter("analyses_total", "Total de análises", ["status"])


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
