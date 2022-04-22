import time
import socket
import struct
import logging
from datetime import datetime
from collections import defaultdict
from typing import List, Optional, DefaultDict

import numpy as np

from metrics_server.utils import get_logger
from metrics_server.constants import Ramp, Intent, Aggregation
from metrics_server.protocol import (
    Query,
    Metric,
    Status,
    MetricResponse,
    IntentionPackage,
    QueryPartialResponse,
)

logger = get_logger(__name__, logging.DEBUG)


class Client:
    def __init__(self, host: str = "localhost", port: int = 5678):
        self.host = host
        self.port = port
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
        except ConnectionRefusedError:
            logger.error("Connection refused")
            raise

    def send(self, buffer):
        self.socket.sendall(buffer)

    def receive(self, cls):
        buffer = self.socket.recv(struct.calcsize(cls.fmt))
        return cls.from_bytes(buffer)

    def send_query(
        self,
        metric: str,
        agg: Aggregation,
        agg_window: float,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> List[int]:
        logger.info("Sending intent")
        self.send(IntentionPackage(Intent.query).to_bytes())

        logger.info("Sending query")
        self.send(Query(metric, agg, agg_window, start, end).to_bytes())

        logger.info("Query sent, awaiting response")

        status = []
        while True:
            response = self.receive(QueryPartialResponse)
            if response.is_empty:
                break

            if response.error:
                # TODO
                pass
            status.append(response.aggvalue)
            if response.last:
                break

        return status

    def _send_metric(self, metric, value):
        logger.info("Sending message")
        self.send(Metric(metric, value).to_bytes())

        logger.info("Message sent, awaiting response")
        status = self.receive(MetricResponse)

        if status.error:
            logger.error("Got error: %s", status.msg)
        else:
            logger.info("Message received correctly!")

        return status

    def send_metric(self, metric: str, value: int) -> MetricResponse:
        logger.info("Sending intent")
        self.send(IntentionPackage(Intent.metric).to_bytes())

        return self._send_metric(metric, value)

    def ramp_metric(
        self, strategy: Ramp, metric: str, during: int, initial: int, final: int
    ):
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
