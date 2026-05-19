"""Shared logging helpers for Friday orchestration modules.

Configures Python logging with a Rich handler so the new orchestration
stack emits structured, readable logs without using print().
"""
from __future__ import annotations

import logging

try:
    from rich.console import Console
    from rich.logging import RichHandler
except ImportError:  # pragma: no cover - fallback for minimal environments
    Console = None
    RichHandler = None


_CONSOLE = Console() if Console is not None else None
_CONFIGURED = False


def configure_logging(name: str | None = None, level: int = logging.INFO) -> logging.Logger:
    """Return a logger configured with a Rich handler on first use."""
    global _CONFIGURED

    root = logging.getLogger()
    if not _CONFIGURED:
        if RichHandler is not None:
            if not any(isinstance(handler, RichHandler) for handler in root.handlers):
                root.addHandler(
                    RichHandler(
                        console=_CONSOLE,
                        rich_tracebacks=True,
                        markup=True,
                        show_time=True,
                        show_path=False,
                    )
                )
        elif not root.handlers:
            root.addHandler(logging.StreamHandler())
        root.setLevel(level)
        _CONFIGURED = True

    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
