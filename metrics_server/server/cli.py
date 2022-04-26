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
    host: str = typer.Option(
        cfg.server.host(default=DEFAULT_HOST), help="Host to bind server to"
    ),
    port: int = typer.Option(
        cfg.server.port(default=DEFAULT_PORT, cast=int),
        help="Port to bind the server to",
    ),
    workers: int = typer.Option(
        cfg.server.workers(default=DEFAULT_WORKERS, cast=int),
        help="Amount of processes handling metrics",
    ),
    backlog: int = typer.Option(
        cfg.server.backlog(default=DEFAULT_BACKLOG, cast=int),
        help="How many unaccepted connections the system allows before refusing new ones",
    ),
    writers: int = typer.Option(
        cfg.server.writers(default=DEFAULT_WRITERS, cast=int),
        help="Amount of processes writing metrics to disk",
    ),
    queriers: int = typer.Option(
        cfg.server.queriers(default=DEFAULT_QUERIERS, cast=int),
        help="Amount of processes handling queries",
    ),
    notifiers: int = typer.Option(
        cfg.server.notifiers(default=DEFAULT_NOTIFIERS, cast=int),
        help="Amount of processes reviewing active notifications",
    ),
    data_path: pathlib.Path = typer.Option(
        cfg.server.data_path(default=DEFAULT_DATA_PATH, cast=pathlib.Path),
        help="Path to save data to",
    ),
    notifications_log_path: pathlib.Path = typer.Option(
        cfg.server.notifications_log_path(
            default=DEFAULT_NOTIFICATIONS_LOG_PATH, cast=pathlib.Path
        ),
        help="Path to write notification messages to",
    ),
    notifications_cfg: str = typer.Option(
        cfg.server.notifications_cfg(
            default=str(DEFAULT_NOTIFICATIONS_FILE),
        ),
        help="Path to notifications configuration ini file",
    ),
    verbose: int = typer.Option(
        DEFAULT_VERBOSE,
        "--verbose",
        "-v",
        count=True,
        help="Level of verbosity. Can be passed more than once for more levels of logging.",
    ),
    pretty: bool = typer.Option(
        DEFAULT_PRETTY,
        "--pretty",
        help="Whether to pretty print the logs with colors",
    ),
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
