import zlib
import queue
import signal
import socket
import struct
import pathlib
import multiprocessing
from typing import List

from metrics_server.utils import get_logger
from metrics_server.protocol import Metric, Status, MetricResponse, ReceivedMetric

logger = get_logger(__name__)

BUFSIZE = 1024


def handle_conn(
    conns_queue: multiprocessing.Queue, metrics_queues: List[multiprocessing.Queue]
):
    try:
        while True:
            sock, addr = conns_queue.get()
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
        logger.info("Client closed connection before I could respond")
    except OSError:
        logger.info("Error while reading socket")
    except KeyboardInterrupt:
        logger.info("Got keyboard interrupt, exiting")
    except:  # pylint: disable=bare-except
        logger.error("Got unknown exception", exc_info=True)
    finally:
        logger.info("Exiting")
        try:
            sock.close()
        except UnboundLocalError:
            pass


def write_metrics(data_path: pathlib.Path, metrics_queue: multiprocessing.Queue):
    while True:
        received_metric = metrics_queue.get()
        partition_minute = int(received_metric.timestamp // 60)
        metric = received_metric.identifier

        file_path = data_path / metric / str(partition_minute)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "a") as f:
            f.write(
                f"{received_metric.timestamp},{received_metric.identifier},{received_metric.value}\n"
            )


class Server:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5678,
        workers: int = 16,
        backlog: int = 10,
        writers: int = 8,
        data_path: pathlib.Path = pathlib.Path("/tmp"),
    ):
        self.host = host
        self.port = port
        self.workers = workers
        self.listen_backlog = backlog
        self.data_path = data_path

        self.connections_queue: multiprocessing.Queue = multiprocessing.Queue()

        self.metrics_queues: List[multiprocessing.Queue] = [
            multiprocessing.Queue() for _ in range(writers)
        ]
        self.writers = [
            multiprocessing.Process(
                target=write_metrics, args=(self.data_path, self.metrics_queues[i])
            )
            for i in range(writers)
        ]

        self.runners = [
            multiprocessing.Process(
                target=handle_conn, args=(self.connections_queue, self.metrics_queues)
            )
            for _ in range(workers)
        ]

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            logger.error("Could not open socket", exc_info=True)
            raise RuntimeError("Socket error")

        try:
            self._server_socket.bind(("", port))
            self._server_socket.listen(self.listen_backlog)
        except socket.error:
            logger.error("Could not bind socket", exc_info=True)
            raise RuntimeError("Socket binding error")

        self._signaled_termination = False
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, *_args):
        logger.debug("Got SIGTERM, exiting gracefully")
        logger.debug("Force stopping all children threads")
        for runner in self.runners:
            runner.terminate()
        for writer in self.writers:
            writer.terminate()

        self._signaled_termination = True
        self._server_socket.close()

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        for p in self.writers:
            p.start()

        for p in self.runners:
            p.start()

        try:
            while not self._signaled_termination:
                client_sock, client_addr = self._accept_new_connection()
                self.connections_queue.put((client_sock, client_addr))
        except queue.Full:
            pass
            # TODO: send error
        except KeyboardInterrupt:
            for runner in self.runners:
                runner.terminate()
            for writer in self.writers:
                writer.terminate()
            self._signaled_termination = True
            self._server_socket.close()

    def _accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logger.info("Proceed to accept new connections")
        conn, addr = self._server_socket.accept()

        logger.info(f"Got connection from {addr}")
        return conn, addr
