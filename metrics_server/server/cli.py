import pathlib

import typer

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
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    workers: int = DEFAULT_WORKERS,
    backlog: int = DEFAULT_BACKLOG,
    writers: int = DEFAULT_WRITERS,
    queriers: int = DEFAULT_QUERIERS,
    data_path: pathlib.Path = DEFAULT_DATA_PATH,
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
