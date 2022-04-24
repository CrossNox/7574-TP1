import zlib
import struct
import pathlib
import multiprocessing
from typing import List

from metrics_server.utils import get_logger, minute_partition
from metrics_server.protocol import Metric, Status, MetricResponse, ReceivedMetric

logger = get_logger(__name__)


def handle_metrics_conns(
    metrics_conns_queue: multiprocessing.Queue,
    metrics_queues: List[multiprocessing.Queue],
):
    try:
        while True:
            sock, addr = metrics_conns_queue.get()
            while True:
                # Receive metric
                buffer = sock.recv(struct.calcsize(Metric.fmt))
                if buffer == b"":
                    break

                thing = Metric.from_bytes(buffer)
                logger.info("received: %s from %s", thing, addr)

                # Reply an ack
                metric_response = MetricResponse(Status.ok)
                sock.sendall(metric_response.to_bytes())

                # Send to queues for processing
                shard = zlib.crc32(thing.identifier.encode()) % len(metrics_queues)
                metrics_queues[shard].put(ReceivedMetric.from_metric(thing))

    except ConnectionResetError:
        logger.error("Client closed connection before I could respond")
    except OSError:
        logger.error("Error while reading socket", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Got keyboard interrupt")
    except:  # pylint: disable=bare-except
        logger.error("Got unknown exception", exc_info=True)
    finally:
        logger.info("Exiting")
        try:
            sock.close()
        except UnboundLocalError:
            pass


def write_metrics(data_path: pathlib.Path, metrics_queue: multiprocessing.Queue):
    try:
        while True:
            received_metric = metrics_queue.get()
            partition_minute = minute_partition(received_metric.timestamp)
            metric = received_metric.identifier

            file_path = data_path / metric / str(partition_minute)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "a") as f:
                f.write(
                    f"{received_metric.timestamp},{received_metric.identifier},{received_metric.value}\n"
                )
    except KeyboardInterrupt:
        logger.info("Got keyboard interrupt")
    except:  # pylint: disable=bare-except
        logger.error("write_metrics err", exc_info=True)
    finally:
        logger.info("Exiting")
