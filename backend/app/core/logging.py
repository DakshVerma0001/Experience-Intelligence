import logging
import re
import sys

_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|secret|token|api[_-]?key)\s*[=:]\s*\S+"),
]


class RedactingFilter(logging.Filter):
    """Prevents secrets/tokens/passwords from ever reaching log output."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pattern in _SECRET_PATTERNS:
            if pattern.search(msg):
                record.msg = pattern.sub(lambda m: m.group(0).split("=")[0].split(":")[0] + "=[REDACTED]", msg)
                record.args = ()
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactingFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
