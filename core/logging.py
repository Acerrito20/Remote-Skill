"""Structured JSON Lines logging via structlog."""

import logging
import sys

try:
    import structlog

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )

    def get_logger(name: str):
        return structlog.get_logger(name)

except ImportError:
    # Fallback to stdlib if structlog not installed.
    logging.basicConfig(
        stream=sys.stderr,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    def get_logger(name: str):
        return logging.getLogger(name)


log = get_logger("cdg")
