import signal
import socket
import struct
import multiprocessing

from metrics_server.utils import get_logger
from metrics_server.protocol import Metric, Status, MetricResponse

logger = get_logger(__name__)

BUFSIZE = 1024


def handle_receive_metric(sock, addr):
    # TODO: save to file
    try:
        buffer = sock.recv(struct.calcsize(Metric.fmt))
        thing = Metric.from_bytes(buffer)
        logger.info("received: %s from %s", thing, addr)
        metric_response = MetricResponse(Status.ok)
        sock.sendall(metric_response.to_bytes())
    except ConnectionResetError:
        logger.info("Client closed connection before I could respond")
    except OSError:
        logger.info("Error while reading socket")
    finally:
        sock.close()


class Server:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5678,
        workers: int = 16,
        backlog: int = 10,
    ):
        self.host = host
        self.port = port
        self.workers = workers
        self.listen_backlog = backlog
        self.runners = multiprocessing.Pool(workers)

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
        self.runners.terminate()
        self._signaled_termination = True
        self._server_socket.close()

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        try:
            while not self._signaled_termination:
                client_sock, client_addr = self._accept_new_connection()
                _ = self.runners.apply_async(
                    handle_receive_metric, args=(client_sock, client_addr)
                )
                # TODO: keep the AsyncResult and get the inner result
                # https://docs.python.org/3.9/library/multiprocessing.html#multiprocessing.pool.AsyncResult
        except KeyboardInterrupt:
            self.runners.terminate()
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
