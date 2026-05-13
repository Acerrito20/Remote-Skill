"""Structured JSON Lines logging via structlog."""

import logging
import sys

try:
    import structlog

    # Use native structlog BoundLogger + PrintLoggerFactory. Original config
    # mixed stdlib processors (add_logger_name expects logger.name) with the
    # non-stdlib PrintLoggerFactory (no .name attr) and crashed at first log call.
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )

    def get_logger(name: str):
        # Bind logger name as an event field instead of relying on add_logger_name.
        return structlog.get_logger().bind(logger=name)

except ImportError:
    # Fallback to stdlib if structlog not installed.
    logging.basicConfig(
        stream=sys.stderr,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    def get_logger(name: str):
        return logging.getLogger(name)


log = get_logger("cdg")
