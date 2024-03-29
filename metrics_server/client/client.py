import time
import socket
import struct
from datetime import datetime
from collections import defaultdict
from typing import List, Type, Optional, DefaultDict

import numpy as np

from metrics_server.utils import get_logger
from metrics_server.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_RETRIES,
    Ramp,
    Intent,
    Aggregation,
)
from metrics_server.protocol import (
    Query,
    Metric,
    Status,
    MetricResponse,
    ProtocolMessage,
    IntentionPackage,
    NotificationResponse,
    QueryPartialResponse,
)

logger = get_logger(__name__)


class Client:
    """Client to make requests to metrics server."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        retries: int = DEFAULT_RETRIES,
    ):
        self.host = host
        self.port = port
        try:
            logger.info("Attempting to connect to %s:%s", self.host, self.port)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            while retries:
                try:
                    self.socket.connect((host, port))
                    logger.info("Connected to server")
                    break
                except ConnectionRefusedError:
                    retries -= 1
                    logger.error(
                        "Connection refused - retry - %s attempts left", retries
                    )
                    if retries == 0:
                        raise
                    time.sleep(5)
        except ConnectionRefusedError:
            logger.error("Connection refused")
            raise

    def __del__(self):
        self.socket.close()

    def send(self, buffer):
        """Send a buffer to server."""
        self.socket.sendall(buffer)

    def receive(self, cls: Type[ProtocolMessage]):
        """Receive bytes from buffer.

        Args:
            cls: Class to receive bytes for.

        Returns:
            An object from the passed class.
        """
        buffer = self.socket.recv(struct.calcsize(cls.fmt))
        return cls.from_bytes(buffer)

    def monitor_notifications(self):
        """Monitor notifications from server."""
        try:
            logger.info("Sending intent")
            self.send(IntentionPackage(Intent.monitor).to_bytes())

            while True:
                new_notification = self.receive(NotificationResponse)
                if new_notification.error:
                    raise ValueError(new_notification.msg)

                if new_notification.stopping:
                    break

                yield (new_notification.dt, new_notification.message)

        except KeyboardInterrupt:
            pass

    def send_query(
        self,
        metric: str,
        agg: Aggregation,
        agg_window: float,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> List[int]:
        """Send a query to the server.

        Args:
            metric: id of the metric to query about.
            agg: aggregation to use.
            agg_window: how many seconds the aggregation window lasts.
            start: begin of the query period.
            end: end of the query period.

        Returns:
            List with values aggregated
        """
        logger.info("Sending intent")
        self.send(IntentionPackage(Intent.query).to_bytes())

        logger.info("Sending query")
        self.send(Query(metric, agg, agg_window, start, end).to_bytes())

        logger.info("Query sent, awaiting response")

        status = []
        while True:
            response = self.receive(QueryPartialResponse)

            if response.error:
                raise ValueError(response.msg)

            status.append(response.aggvalue)
            if response.last:
                break

        return status

    def _send_metric(self, metric, value):
        """Send a metric to the server."""
        logger.info("Sending message")
        self.send(Metric(metric, value).to_bytes())

        logger.info("Message sent, awaiting response")
        status = self.receive(MetricResponse)

        if status.error:
            raise ValueError(status.msg)

        logger.info("Message received correctly!")

        return status

    def send_metric(self, metric: str, value: int) -> MetricResponse:
        """Send a single metric to the server.

        Args:
            metric: id of the metric to send.
            value: value associated to the metric observation.

        Returns:
            A response by the server.
        """
        logger.info("Sending intent")
        self.send(IntentionPackage(Intent.metric).to_bytes())

        return self._send_metric(metric, value)

    def ramp_metric(
        self, strategy: Ramp, metric: str, during: int, initial: int, final: int
    ):
        """Send several metric observations to the server.

        Prints statistics of sent metric observations.

        Args:
            strategy: how to scale the amount of metrics per second between initial
                and final values.
            metric: id of the metric to send.
            during: how long the ramp will last.
            initial: initial amount of queries per second.
            final: final amount of queries per second.

        Returns:
            Nothing.
        """
        logger.info("Calculating messages rate")
        if strategy == Ramp.exponential:
            msgs_rate = np.logspace(
                np.log2(initial), np.log2(final), num=during, base=2
            ).astype(int)
        elif strategy == Ramp.linear:
            msgs_rate = np.linspace(initial, final, num=during).astype(int)
        else:
            msgs_rate = np.repeat(initial, during).astype(int)

        aggs: DefaultDict[Status, int] = defaultdict(lambda: 0)
        times = []

        logger.info("Sending intent")
        self.send(IntentionPackage(Intent.metric).to_bytes())

        i = 1
        for rate in msgs_rate:
            for _ in range(rate):
                tts = 1.0 / rate
                t1 = time.time()
                metric_response = self._send_metric(metric, i)
                t2 = time.time()
                if metric_response.status == Status.ok:
                    times.append((t2 - t1) * 1000.0)
                aggs[metric_response.status] += 1
                # TODO: sleep delta
                time.sleep(tts)
                i += 1

        logger.info("Stats: %s", {k: v for k, v in aggs.items()})
        logger.info("Avg %s", np.mean(times))
        logger.info("Min %s", np.min(times))
        logger.info("Max %s", np.max(times))
        logger.info("P50 %s", np.percentile(times, 50))
        logger.info("P90 %s", np.percentile(times, 90))
        logger.info("P95 %s", np.percentile(times, 95))
        logger.info("P99 %s", np.percentile(times, 99))
