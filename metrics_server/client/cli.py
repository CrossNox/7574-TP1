from typing import Optional
from datetime import datetime

import typer

from metrics_server.cfg import cfg
from metrics_server.client.client import Client
from metrics_server.constants import DEFAULT_HOST, DEFAULT_PORT, Ramp, Aggregation
from metrics_server.utils import (
    DEFAULT_PRETTY,
    DEFAULT_VERBOSE,
    get_logger,
    config_logging,
)

logger = get_logger(__name__)

app = typer.Typer()


@app.command()
def ramp(
    strategy: Ramp,
    metric: str,
    during: int,
    initial: int,
    final: int,
    host: str = cfg.server.host(default=DEFAULT_HOST),
    port: int = cfg.server.port(default=DEFAULT_PORT, cast=int),
):
    try:
        Client(host, port).ramp_metric(strategy, metric, during, initial, final)
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")
    except ValueError as e:
        logger.error(e)


@app.command()
def send(
    metric: str,
    value: int,
    host: str = cfg.server.host(default=DEFAULT_HOST),
    port: int = cfg.server.port(default=DEFAULT_PORT, cast=int),
):
    try:
        Client(host, port).send_metric(metric, value)
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")
    except ValueError as e:
        logger.error(e)


@app.command()
def query(
    metric: str,
    agg: Aggregation,
    agg_window: float,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    host: str = cfg.server.host(default=DEFAULT_HOST),
    port: int = cfg.server.port(default=DEFAULT_PORT, cast=int),
):
    try:
        assert agg_window >= 0
        agg_array = Client(host, port).send_query(metric, agg, agg_window, start, end)
        typer.echo("Aggregation: " + typer.style(agg_array, fg=typer.colors.GREEN))
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")
    except ValueError as e:
        logger.error(e)


@app.command()
def monitor(
    host: str = cfg.server.host(default=DEFAULT_HOST),
    port: int = cfg.server.port(default=DEFAULT_PORT, cast=int),
):
    try:
        Client(host, port).monitor_notifications()
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")


@app.callback()
def main(
    verbose: int = typer.Option(DEFAULT_VERBOSE, "--verbose", "-v", count=True),
    pretty: bool = typer.Option(DEFAULT_PRETTY, "--pretty"),
):
    config_logging(verbose, pretty)


if __name__ == "__main__":
    app()
