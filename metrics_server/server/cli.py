import pathlib

import typer
from youconfigme import Config

from metrics_server.cfg import cfg
from metrics_server.server.server import Server
from metrics_server.utils import (
    DEFAULT_PRETTY,
    DEFAULT_VERBOSE,
    get_logger,
    config_logging,
)
from metrics_server.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_BACKLOG,
    DEFAULT_WORKERS,
    DEFAULT_WRITERS,
    DEFAULT_QUERIERS,
    DEFAULT_DATA_PATH,
    DEFAULT_NOTIFIERS,
    DEFAULT_NOTIFICATIONS_FILE,
    DEFAULT_NOTIFICATIONS_LOG_PATH,
)

logger = get_logger(__name__)
app = typer.Typer()


@app.command()
def main(
    host: str = cfg.server.host(default=DEFAULT_HOST),
    port: int = cfg.server.port(default=DEFAULT_PORT, cast=int),
    workers: int = cfg.server.workers(default=DEFAULT_WORKERS, cast=int),
    backlog: int = cfg.server.backlog(default=DEFAULT_BACKLOG, cast=int),
    writers: int = cfg.server.writers(default=DEFAULT_WRITERS, cast=int),
    queriers: int = cfg.server.queriers(default=DEFAULT_QUERIERS, cast=int),
    notifiers: int = cfg.server.notifiers(default=DEFAULT_NOTIFIERS, cast=int),
    data_path: pathlib.Path = cfg.server.data_path(
        default=DEFAULT_DATA_PATH, cast=pathlib.Path
    ),
    notifications_log_path: pathlib.Path = cfg.server.notifications_log_path(
        default=DEFAULT_NOTIFICATIONS_LOG_PATH, cast=pathlib.Path
    ),
    notifications_cfg: str = cfg.server.notifications_cfg(
        default=str(DEFAULT_NOTIFICATIONS_FILE),
    ),
    verbose: int = typer.Option(DEFAULT_VERBOSE, "--verbose", "-v", count=True),
    pretty: bool = typer.Option(DEFAULT_PRETTY, "--pretty"),
):
    config_logging(verbose, pretty)
    server = Server(
        host=host,
        port=port,
        workers=workers,
        backlog=backlog,
        writers=writers,
        queriers=queriers,
        notifiers=notifiers,
        data_path=data_path,
        notifications_log_path=notifications_log_path,
        notifications=Config(from_items=notifications_cfg),
    )
    server.run()


if __name__ == "__main__":
    app()
