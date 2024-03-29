import queue
import socket
import pathlib
import multiprocessing
from typing import List
from datetime import datetime, timedelta

from metrics_server.utils import get_logger
from metrics_server.client.client import Client
from metrics_server.constants import Aggregation
from metrics_server.protocol import NotificationResponse

logger = get_logger(__name__)


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
        self.next_eval = datetime.now() + timedelta(
            seconds=self.aggregation_window_secs
        )

    @property
    def is_due(self):
        return self.next_eval <= datetime.now()

    def bump_eval(self):
        """Bump the next evaluation time."""
        self.prev_eval = self.next_eval
        if not self.on:
            self.next_eval += timedelta(seconds=self.aggregation_window_secs)
        else:
            self.next_eval += timedelta(seconds=60)

    def toggle(self):
        self.on = not self.on


def handle_notifications_messages(
    notifications_log_path: pathlib.Path,
    notifications_messages_queue: multiprocessing.Queue,
    monitoring_conns_queue: multiprocessing.Queue,
):
    """Handle messages from triggered notifications.

    Args:
        notifications_log_path: Path where to log notifications to.
        notifications_messages_queue: Queue where notification messages are placed.
        monitoring_conns_queue: Queue where connections declaring intention to
            monitor notification messages are placed.

    Returns:
        None
    """
    monitor_clients: List[socket.socket] = []
    try:
        notifications_log_path.touch(exist_ok=True)

        while True:
            try:
                (notification_name, dt, triggerval) = notifications_messages_queue.get(
                    timeout=5
                )
                msg = f"Notification {notification_name} over the limit with value {triggerval}"

                _monitor_clients = []
                for monitor_client in monitor_clients:
                    try:
                        logger.info("Sending to some listener")
                        monitor_client.sendall(NotificationResponse(dt, msg).to_bytes())
                        _monitor_clients.append(monitor_client)
                    except BrokenPipeError:
                        # Remove this from the internal list,
                        # since it has most likely disconnected.
                        pass
                    finally:
                        monitor_clients = _monitor_clients

                with open(notifications_log_path, "a") as f:
                    f.write(f"{dt} - {msg}\n")
            except queue.Empty:
                try:
                    (conn, _) = monitoring_conns_queue.get(timeout=0)
                    monitor_clients.append(conn)
                except queue.Empty:
                    pass

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
    """Check for notifications triggering.

    Args:
        notifications_queue: queue where notifications are placed.
        port: port of the server running.
        host: host where the server is running.
        notifications_messages_queue: queue where triggered notification messages
            should be placed.

    Returns:
        None
    """
    try:
        while True:
            notification = notifications_queue.get()

            if not notification.is_due:
                notifications_queue.put(notification)
                continue

            client = Client(host=host, port=port)
            try:
                res = client.send_query(
                    notification.metric,
                    notification.agg,
                    notification.aggregation_window_secs,
                    notification.prev_eval,
                    notification.next_eval,
                )

                if any(x >= notification.limit for x in res):
                    # We are over the threshold, alarm is on
                    notifications_messages_queue.put(
                        (notification.name, datetime.now(), max(res))
                    )
                    if not notification.on:
                        notification.toggle()
                elif notification.on:
                    # We are not over the threshold anymore
                    notification.toggle()
            except ValueError:
                pass
            finally:
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
