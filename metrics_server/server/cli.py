import pathlib

import typer

from metrics_server.cfg import cfg
from metrics_server.utils import get_logger
from metrics_server.server.server import Server
from metrics_server.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_BACKLOG,
    DEFAULT_WORKERS,
    DEFAULT_WRITERS,
    DEFAULT_QUERIERS,
    DEFAULT_DATA_PATH,
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
    data_path: pathlib.Path = cfg.server.data_path(
        default=DEFAULT_DATA_PATH, cast=pathlib.Path
    ),
):
    server = Server(
        host=host,
        port=port,
        workers=workers,
        backlog=backlog,
        writers=writers,
        queriers=queriers,
        data_path=data_path,
    )
    server.run()


if __name__ == "__main__":
    app()
