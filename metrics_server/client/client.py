import socket
import struct

from metrics_server.utils import get_logger

logger = get_logger(__name__)


class Client:
    def __init__(self, host: str = "localhost", port: int = 5678):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))

    def send(self, buffer):
        self.socket.sendall(buffer)

    def receive(self, cls):
        buffer = self.socket.recv(struct.calcsize(cls.fmt))
        return cls.from_bytes(buffer)
