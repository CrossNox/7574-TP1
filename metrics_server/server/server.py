import glob
import zlib
import queue
import signal
import socket
import struct
import pathlib
import multiprocessing
from typing import List, Optional
from datetime import datetime, timedelta

import pandas as pd
import youconfigme as ycm

from metrics_server.client.client import Client
from metrics_server.utils import get_logger, minute_partition
from metrics_server.exceptions import EmptyAggregationArray, InvalidNotificationSetting
from metrics_server.protocol import (
    Query,
    Metric,
    Status,
    MetricResponse,
    ReceivedMetric,
    IntentionPackage,
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
    Intent,
    Aggregation,
)

logger = get_logger(__name__)

BUFSIZE = 1024


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


def handle_queries(queries_conns_queue: multiprocessing.Queue, data_path: pathlib.Path):
    try:
        while True:
            sock, addr = queries_conns_queue.get()
            buffer = sock.recv(struct.calcsize(Query.fmt))

            query = Query.from_bytes(buffer)
            logger.info("query: %s from %s", query, addr)

            try:
                agg = agg_metrics(
                    data_path,
                    query.metric,
                    query.agg,
                    query.agg_window,
                    query.start,
                    query.end,
                )

                logger.info("Got %s metrics to send", len(agg))

                for idx, value in enumerate(agg):
                    is_last = idx == (len(agg) - 1)
                    partial_response = QueryPartialResponse(Status.ok, value, is_last)
                    sock.sendall(partial_response.to_bytes())

            except EmptyAggregationArray:
                partial_response = QueryPartialResponse.emtpy()
                sock.sendall(partial_response.to_bytes())

            finally:
                sock.close()

    except ConnectionResetError:
        logger.info("Client closed connection before I could respond")
    except OSError:
        logger.info("Error while reading socket")
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


def agg_metrics(
    data_path: pathlib.Path,
    metric: str,
    agg: Aggregation,
    agg_window: float,
    start: Optional[datetime],
    end: Optional[datetime],
) -> List[float]:
    dfs = []

    for partition in glob.glob(str(data_path / metric / "*")):
        filename = pathlib.Path(partition)

        if start is not None and int(filename.name) < minute_partition(
            start.timestamp()
        ):
            continue

        if end is not None and int(filename.name) > minute_partition(end.timestamp()):
            continue

        df = pd.read_csv(filename, names=["ts", "metric", "value"], engine="c")
        df.ts = df.ts.apply(datetime.fromtimestamp)

        if start is not None:
            df = df[df.ts >= start]

        if end is not None:
            df = df[df.ts <= end]

        dfs.append(df)

    if len(dfs) == 0:
        raise EmptyAggregationArray()

    df = pd.concat(dfs)

    if len(df) == 0:
        raise EmptyAggregationArray()

    df.sort_values("ts", inplace=True, ascending=True)

    if agg_window == 0.0:
        return df.value.tolist()

    df["offset"] = (df.ts - df.ts.iloc[0]).dt.total_seconds() // agg_window

    return df.groupby("offset").value.agg(agg.value).values.tolist()


def dispatch_conn(connections_queue, metrics_conns_queue, queries_conns_queue):
    try:
        while True:
            sock, addr = connections_queue.get()

            buffer = sock.recv(struct.calcsize(IntentionPackage.fmt))
            intention_package = IntentionPackage.from_bytes(buffer)

            if intention_package.intent == Intent.metric:
                metrics_conns_queue.put((sock, addr))
            elif intention_package.intent == Intent.query:
                queries_conns_queue.put((sock, addr))

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


class Notification:
    def __init__(
        self,
        name: str,
        metric: str,
        agg: Aggregation,
        aggregation_window_secs: float,
        limit: float,
    ):
        self.name = name
        self.metric = metric
        self.agg = agg
        self.aggregation_window_secs = aggregation_window_secs
        self.limit = limit
        self.on = False

        self.prev_eval = datetime.now()
        self.next_eval = datetime.now()
        self.bump_eval()

    @property
    def is_due(self):
        return self.next_eval <= datetime.now()

    def bump_eval(self):
        self.prev_eval = self.next_eval
        if not self.on:
            self.next_eval += timedelta(seconds=self.aggregation_window_secs)
        else:
            self.next_eval += timedelta(seconds=60)

    def toggle(self):
        self.on = not self.on


def handle_notifications_messages(
    data_path: pathlib.Path, notifications_messages_queue: multiprocessing.Queue
):
    try:
        notifications_path = pathlib.Path(data_path / "notifications")
        notifications_path.touch(exist_ok=True)

        while True:
            (notification_name, dt) = notifications_messages_queue.get()
            with open(notifications_path, "a") as f:
                f.write(f"{dt} - Notification {notification_name} over the limit")

    except KeyboardInterrupt:
        logger.info("Got keyboard interrupt")
    except:  # pylint: disable=bare-except
        logger.error("Unkown errors", exc_info=True)
    finally:
        logger.info("Exiting")


def watch_notifications(
    notifications_queue: multiprocessing.Queue,
    port: int,
    host: str,
    notifications_messages_queue: multiprocessing.Queue,
):
    try:
        while True:
            notification = notifications_queue.get()

            if not notification.is_due:
                notifications_queue.put(notification)
                continue

            client = Client(host=host, port=port)
            res = client.send_query(
                notification.metric,
                notification.agg,
                notification.aggregation_window_secs,
                notification.prev_eval,
                notification.next_eval,
            )
            # del client

            if any(x >= notification.limit for x in res):
                notifications_messages_queue.put((notification.name, datetime.now()))
                if not notification.on:
                    notification.toggle()
            elif notification.on:
                notification.toggle()

            notification.bump_eval()

            notifications_queue.put(notification)
    except ConnectionRefusedError:
        logger.error("Conn closed", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Got keyboard interrupt")
    except:  # pylint: disable=bare-except
        logger.error("Unkown errors", exc_info=True)
    finally:
        logger.info("Exiting")


class Server:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        workers: int = DEFAULT_WORKERS,
        backlog: int = DEFAULT_BACKLOG,
        writers: int = DEFAULT_WRITERS,
        queriers: int = DEFAULT_QUERIERS,
        notifiers: int = 4,
        data_path: pathlib.Path = DEFAULT_DATA_PATH,
        notifications: ycm.Config = ycm.AutoConfig(
            filename="notifications.ini", max_up_levels=4
        ),
    ):
        self.host = host
        self.port = port
        self.workers = workers
        self.listen_backlog = backlog
        self.data_path = data_path
        self.notifications = notifications

        # Queues
        self.connections_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.metrics_conns_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.queries_conns_queue: multiprocessing.Queue = multiprocessing.Queue()
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
            args=(data_path, self.notifications_messages_queue),
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
                self.connections_queue.put((client_sock, client_addr))
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
