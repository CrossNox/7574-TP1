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
    Client(host, port).send_metric(metric, value)


@app.command()
def query(
    metric: str,
    agg: Aggregation,
    agg_window: float,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    assert agg_window > 0
    logger.info("%s %s %s %s %s", metric, start, end, agg, agg_window)


if __name__ == "__main__":
    app()
