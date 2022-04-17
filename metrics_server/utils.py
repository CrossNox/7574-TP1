"""Utils file."""
import logging

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
            fg = typer.colors.BRIGHT_WHITE
            bg = typer.colors.BRIGHT_RED
        typer.secho(self.format(record), bg=bg, fg=fg)


def config_logging(level: int = logging.DEBUG):
    """Configure logging for stream and file."""
    logger = logging.getLogger()
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    typer_handler = TyperLoggerHandler()
    typer_handler.setLevel(level)
    typer_handler.setFormatter(formatter)
    logger.addHandler(typer_handler)


def get_logger(name: str, to_file: bool = False):
    logger = logging.getLogger(name)

    if to_file:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        try:
            file_handler = logging.FileHandler(f"{name}.log")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            pass

    return logger
