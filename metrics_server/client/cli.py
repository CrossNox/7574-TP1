from typing import Optional
from datetime import datetime

import typer

from metrics_server.utils import get_logger
from metrics_server.client.client import Client
from metrics_server.constants import DEFAULT_HOST, DEFAULT_PORT, Ramp, Aggregation

logger = get_logger(__name__)

app = typer.Typer()


@app.command()
def ramp(
    strategy: Ramp,
    metric: str,
    during: int,
    initial: int,
    final: int,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
):
    Client(host, port).ramp_metric(strategy, metric, during, initial, final)


@app.command()
def send(
    metric: str,
    value: int,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
):
    try:
        Client(host, port).send_metric(metric, value)
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")


@app.command()
def query(
    metric: str,
    agg: Aggregation,
    agg_window: float,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
):
    assert agg_window >= 0
    logger.info("%s %s %s %s %s", metric, start, end, agg, agg_window)
    agg_array = Client(host, port).send_query(metric, agg, agg_window, start, end)
    typer.echo("Aggregation: " + typer.style(agg_array, fg=typer.colors.GREEN))


if __name__ == "__main__":
    app()
