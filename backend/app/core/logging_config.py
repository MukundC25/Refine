import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

def configure_logging(log_file: str = "logs/ranking_audit.log", level: str = "INFO"):
    """
    Configure structlog for structured JSON output.
    Writes to both console (human-readable) and file (JSON lines).
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors before formatting
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # File handler: JSON lines for machine parsing
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[structlog.processors.JSONRenderer()]
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=50 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)

    # Console handler: colored key=value for development
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[structlog.dev.ConsoleRenderer()]
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)

    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


log = structlog.get_logger()
