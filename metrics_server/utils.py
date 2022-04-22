"""Utils file."""

import logging
from typing import Generator
from datetime import datetime, timedelta

import typer


class TyperLoggerHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        fg = None
        bg = None
        if record.levelno == logging.DEBUG:
            fg = typer.colors.BLACK
            bg = typer.colors.WHITE
        elif record.levelno == logging.INFO:
            fg = typer.colors.BRIGHT_BLUE
        elif record.levelno == logging.WARNING:
            fg = typer.colors.BRIGHT_MAGENTA
        elif record.levelno == logging.CRITICAL:
            fg = typer.colors.BRIGHT_RED
        elif record.levelno == logging.ERROR:
            fg = typer.colors.BLACK
            bg = typer.colors.BRIGHT_RED
        typer.secho(self.format(record), bg=bg, fg=fg)


def get_logger(name: str, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    typer_handler = TyperLoggerHandler()
    typer_handler.setLevel(level)
    typer_handler.setFormatter(formatter)
    logger.addHandler(typer_handler)

    return logger


def minute_range(
    start_date: datetime, end_date: datetime
) -> Generator[datetime, None, None]:
    while start_date <= end_date:
        yield start_date
        start_date += timedelta(minutes=1)


def minute_partition(ts: int) -> int:
    return int(ts // 60)
