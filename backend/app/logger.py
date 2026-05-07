import logging
import sys


class ExtraFormatter(logging.Formatter):
    """
    Custom formatter that appends extra fields to the log message.
    Turns logger.info("Query routed", extra={"route": "rag"})
    into: "2026-05-08 | INFO | app.agents.router | Query routed | route=rag"
    """

    def format(self, record):
        base = super().format(record)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "taskName",
            }
        }
        if extras:
            extra_str = " | ".join(f"{k}={v}" for k, v in extras.items())
            return f"{base} | {extra_str}"
        return base


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ExtraFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
