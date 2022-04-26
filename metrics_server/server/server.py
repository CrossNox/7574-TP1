import queue
import signal
import socket
import struct
import logging
import pathlib
import multiprocessing
from typing import List

import youconfigme as ycm

from metrics_server.utils import get_logger
from metrics_server.server.queries import handle_queries
from metrics_server.exceptions import InvalidNotificationSetting
from metrics_server.server.metrics import write_metrics, handle_metrics_conns
from metrics_server.server.notifications import (
    Notification,
    watch_notifications,
    handle_notifications_messages,
)
from metrics_server.protocol import (
    MetricResponse,
    ProtocolMessage,
    IntentionPackage,
    NotificationResponse,
    QueryPartialResponse,
)
from metrics_server.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_BACKLOG,
    DEFAULT_WORKERS,
    DEFAULT_WRITERS,
    DEFAULT_QUERIERS,
    DEFAULT_DATA_PATH,
    DEFAULT_NOTIFIERS,
    DEFAULT_NOTIFICATIONS_FILE,
    DEFAULT_NOTIFICATIONS_LOG_PATH,
    Intent,
    Aggregation,
)

logger = get_logger(__name__)


def dispatch_conn(
    connections_queue: multiprocessing.Queue,
    metrics_conns_queue: multiprocessing.Queue,
    queries_conns_queue: multiprocessing.Queue,
    monitoring_conns_queue: multiprocessing.Queue,
):
    """Dispatch connections as per their declared intentions.

    Args:
        connections_queue: queue where received connections are placed.
        metrics_conns_queue: queue where connections declaring intention to send a
            metric are to be placed.
        queries_conns_queue: queue where connections declaring intention to make a
            query are to be placed.
        monitoring_conns_queue: queue where connections declaring intention to monitor
            notifications are to be placed.

    Returns:
        None.
    """
    try:
        while True:
            sock, addr = connections_queue.get()

            buffer = sock.recv(struct.calcsize(IntentionPackage.fmt))
            intention_package = IntentionPackage.from_bytes(buffer)
            try:
                if intention_package.intent == Intent.metric:
                    metrics_conns_queue.put((sock, addr))
                elif intention_package.intent == Intent.query:
                    queries_conns_queue.put((sock, addr))
                elif intention_package.intent == Intent.monitor:
                    monitoring_conns_queue.put((sock, addr))
            except queue.Full:
                response: ProtocolMessage
                if intention_package.intent == Intent.metric:
                    response = MetricResponse.server_unavailable()
                elif intention_package.intent == Intent.query:
                    response = QueryPartialResponse.server_unavailable()
                elif intention_package.intent == Intent.monitor:
                    response = NotificationResponse.server_unavailable()
                sock.sendall(response.to_bytes())

    except KeyboardInterrupt:
        logger.info("Got keyboard interrupt")
    except:
        logger.error("dispatch_conn err", exc_info=True)
        raise
    finally:
        try:
            sock.close()
        except UnboundLocalError:
            pass


class Server:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        workers: int = DEFAULT_WORKERS,
        backlog: int = DEFAULT_BACKLOG,
        writers: int = DEFAULT_WRITERS,
        queriers: int = DEFAULT_QUERIERS,
        notifiers: int = DEFAULT_NOTIFIERS,
        data_path: pathlib.Path = DEFAULT_DATA_PATH,
        notifications_log_path: pathlib.Path = DEFAULT_NOTIFICATIONS_LOG_PATH,
        notifications: ycm.Config = ycm.Config(str(DEFAULT_NOTIFICATIONS_FILE)),
    ):
        self.host = host
        self.port = port
        self.workers = workers
        self.listen_backlog = backlog
        self.data_path = data_path
        self.notifications_log_path = notifications_log_path
        self.notifications = notifications

        # Queues
        self.connections_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.metrics_conns_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.queries_conns_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.monitoring_conns_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.metrics_queues: List[multiprocessing.Queue] = [
            multiprocessing.Queue() for _ in range(writers)
        ]
        self.notifications_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.notifications_messages_queue: multiprocessing.Queue = (
            multiprocessing.Queue()
        )

        # Notification messages handler
        self.notifications_messages_handler = multiprocessing.Process(
            target=handle_notifications_messages,
            args=(
                self.notifications_log_path,
                self.notifications_messages_queue,
                self.monitoring_conns_queue,
            ),
        )

        # Notification watchers
        self.notifications_workers: List[multiprocessing.Process] = [
            multiprocessing.Process(
                target=watch_notifications,
                args=(
                    self.notifications_queue,
                    self.port,
                    self.host,
                    self.notifications_messages_queue,
                ),
            )
            for _ in range(notifiers)
        ]

        # Connection dispatcher
        self.conn_dispatcher = multiprocessing.Process(
            target=dispatch_conn,
            args=(
                self.connections_queue,
                self.metrics_conns_queue,
                self.queries_conns_queue,
                self.monitoring_conns_queue,
            ),
        )

        # Metrics writers
        self.writers = [
            multiprocessing.Process(
                target=write_metrics, args=(self.data_path, self.metrics_queues[i])
            )
            for i in range(writers)
        ]

        # Metrics getters
        self.metrics_getters = [
            multiprocessing.Process(
                target=handle_metrics_conns,
                args=(self.metrics_conns_queue, self.metrics_queues),
            )
            for _ in range(workers)
        ]

        self.queries_calculators = [
            multiprocessing.Process(
                target=handle_queries, args=(self.queries_conns_queue, self.data_path)
            )
            for _ in range(queriers)
        ]

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            logger.error("Could not open socket", exc_info=True)
            raise RuntimeError("Socket error")

        try:
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(self.listen_backlog)
            logger.info("Successfully binded at %s", self.port)
        except socket.error:
            logger.error("Could not bind socket", exc_info=True)
            raise RuntimeError("Socket binding error")

        self._signaled_termination = False
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, *_args):
        logger.debug("Got SIGTERM, exiting gracefully")
        logger.debug("Force stopping all children threads")
        self.connections_queue.close()
        self.metrics_conns_queue.close()
        self.queries_conns_queue.close()
        for q in self.metrics_queues:
            q.close()

        self.conn_dispatcher.join()
        for writer in self.writers:
            writer.join()
        for runner in self.metrics_getters:
            runner.join()
        for calculator in self.queries_calculators:
            calculator.join()

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

        for p in self.metrics_getters:
            p.start()

        for p in self.queries_calculators:
            p.start()

        self.notifications_messages_handler.start()

        for p in self.notifications_workers:
            p.start()

        self.conn_dispatcher.start()

        logger.info("Initializing...")

        try:
            try:
                for k, v in self.notifications.to_dict().items():
                    new_notif = Notification(
                        k,
                        v["metric_id"],
                        Aggregation(v["aggregation"]),
                        float(v["aggregation_window_secs"]),
                        float(v["limit"]),
                    )
                    self.notifications_queue.put(new_notif)
            except ValueError:
                logger.error("Invalid notification setting %s", v, exc_info=True)
                raise InvalidNotificationSetting
            except:
                logger.error("Unkown notification setting error", exc_info=True)
                raise InvalidNotificationSetting

            logger.info("starting loop")
            while not self._signaled_termination:
                client_sock, client_addr = self._accept_new_connection()
                try:
                    self.connections_queue.put((client_sock, client_addr))
                except queue.Full:
                    logging.info("Discarding connection")
                    # This might take a while, but gives time for the conn queues to
                    # make some space
                    buffer = client_sock.recv(struct.calcsize(IntentionPackage.fmt))
                    intention_package = IntentionPackage.from_bytes(buffer)

                    response: ProtocolMessage
                    if intention_package.intent == Intent.metric:
                        response = MetricResponse.server_unavailable()
                    elif intention_package.intent == Intent.query:
                        response = QueryPartialResponse.server_unavailable()
                    elif intention_package.intent == Intent.monitor:
                        response = NotificationResponse.server_unavailable()
                    client_sock.sendall(response.to_bytes())

        except queue.Full:
            # TODO: send error
            pass
        except KeyboardInterrupt:
            logger.info("Shutting everything down - keyboard interrupt")
        except InvalidNotificationSetting:
            pass
        finally:
            self.connections_queue.close()
            self.metrics_conns_queue.close()
            self.queries_conns_queue.close()
            for q in self.metrics_queues:
                q.close()

            self.conn_dispatcher.join()
            for writer in self.writers:
                writer.join()
            for runner in self.metrics_getters:
                runner.join()
            for calculator in self.queries_calculators:
                calculator.join()

            self._signaled_termination = True
            self._server_socket.close()

    def _accept_new_connection(self):
        """Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logger.info("Proceed to accept new connections")
        conn, addr = self._server_socket.accept()

        logger.info(f"Got connection from {addr}")
        return conn, addr
