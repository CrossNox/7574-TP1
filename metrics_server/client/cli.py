from datetime import datetime
from typing import Any, Dict, Optional

import typer

from metrics_server.cfg import cfg
from metrics_server.client.client import Client
from metrics_server.utils import (
    DEFAULT_PRETTY,
    DEFAULT_VERBOSE,
    get_logger,
    config_logging,
)
from metrics_server.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_RETRIES,
    Ramp,
    Aggregation,
)

logger = get_logger(__name__)

app = typer.Typer()
CFG: Dict[str, Any] = {}


@app.command()
def ramp(
    strategy: Ramp = typer.Argument(..., help="Ramp up strategy to use"),
    metric: str = typer.Argument(..., help="Metric id to send"),
    during: int = typer.Argument(..., help="Duration of the burst"),
    initial: int = typer.Argument(..., help="Initial amount of RPS"),
    final: int = typer.Argument(..., help="Final amount of RPS"),
):
    """Send a burst of metrics to a server."""
    host = CFG["host"]
    port = CFG["port"]
    retries = CFG["retries"]
    try:
        Client(host, port, retries=retries).ramp_metric(
            strategy, metric, during, initial, final
        )
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")
    except ValueError as e:
        logger.error(e)


@app.command()
def send(
    metric: str = typer.Argument(..., help="Metric id to send"),
    value: int = typer.Argument(..., help="Value of the metric"),
):
    """Send a single metric to a server."""
    host = CFG["host"]
    port = CFG["port"]
    retries = CFG["retries"]
    try:
        Client(host, port, retries=retries).send_metric(metric, value)
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")
    except ValueError as e:
        logger.error(e)


@app.command()
def query(
    metric: str = typer.Argument(..., help="Metric id to send"),
    agg: Aggregation = typer.Argument(..., help="Aggregation function to use"),
    agg_window: float = typer.Argument(..., help="Duration of the aggregation window"),
    start: Optional[datetime] = typer.Option(None, help="Start of the query period"),
    end: Optional[datetime] = typer.Option(None, help="End of the query period"),
):
    """Send a query to the server and print the result."""
    host = CFG["host"]
    port = CFG["port"]
    retries = CFG["retries"]
    try:
        assert agg_window >= 0
        agg_array = Client(host, port, retries=retries).send_query(
            metric, agg, agg_window, start, end
        )
        typer.echo("Aggregation: " + typer.style(agg_array, fg=typer.colors.GREEN))
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")
    except ValueError as e:
        logger.error(e)


@app.command()
def monitor():
    """Monitor triggered notifications."""
    host = CFG["host"]
    port = CFG["port"]
    retries = CFG["retries"]
    try:
        for dt, message in Client(host, port, retries=retries).monitor_notifications():
            # Makes no sense to use logging here
            # We want to print regardless of verbosity
            typer.secho(f"{dt} - {message}")
    except ConnectionRefusedError:
        logger.error("Connection refused, check the host and port")
    except ValueError as e:
        logger.error(e)


@app.callback()
def main(
    host: str = typer.Option(
        cfg.server.host(default=DEFAULT_HOST), help="Host address of the server"
    ),
    port: int = typer.Option(
        cfg.server.port(default=DEFAULT_PORT, cast=int), help="Port of the server"
    ),
    retries: int = typer.Option(
        DEFAULT_RETRIES, help="Retries to connect to the server"
    ),
    verbose: int = typer.Option(
        DEFAULT_VERBOSE,
        "--verbose",
        "-v",
        count=True,
        help="Level of verbosity. Can be passed more than once for more levels of logging.",
    ),
    pretty: bool = typer.Option(
        DEFAULT_PRETTY, "--pretty", help="Whether to pretty print the logs with colors"
    ),
):
    config_logging(verbose, pretty)
    CFG["host"] = host
    CFG["port"] = port
    CFG["retries"] = retries


if __name__ == "__main__":
    app()
