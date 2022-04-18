import typer

from metrics_server.utils import get_logger
from metrics_server.client.client import Client
from metrics_server.protocol import Metric, MetricResponse

logger = get_logger(__name__)

app = typer.Typer()


@app.command()
def send(metric: str, value: int, host: str = "localhost", port: int = 5678):
    logger.info("Sending metric")
    client = Client(host, port)
    client.send(Metric(metric, value).to_bytes())

    logger.info("Metric sent, awaiting response")
    status = client.receive(MetricResponse)

    if status.error:
        logger.error("Got error: %s", status.msg)
    else:
        logger.info("Message received correctly!")


if __name__ == "__main__":
    app()
