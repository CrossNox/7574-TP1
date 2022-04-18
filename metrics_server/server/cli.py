import typer

from metrics_server.utils import get_logger
from metrics_server.server.server import Server

logger = get_logger(__name__)
app = typer.Typer()


@app.command()
def main(host: str = "localhost", port: int = 5678, workers: int = 16):
    server = Server(host, port, workers)
    server.run()


if __name__ == "__main__":
    app()
