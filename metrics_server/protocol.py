import abc
import struct
from enum import Enum


class Status(Enum):
    ok = 1
    server_unavailable = 2
    server_error = 3


class ProtocolMessage(abc.ABC):
    fmt = ""

    @abc.abstractmethod
    def to_bytes(self):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, buffer):
        raise NotImplementedError()


class Metric:
    fmt = "!28sL"

    def __init__(self, identifier: str, value: int):
        self.identifier = identifier
        self.value = value

    def to_bytes(self):
        return struct.pack(Metric.fmt, self.identifier.encode(), self.value)

    @classmethod
    def from_bytes(cls, buffer):
        identifier, value = struct.unpack(Metric.fmt, buffer)
        return Metric(identifier.decode(), value)

    def __str__(self):
        return f"metric: {self.identifier} -> {self.value}"


class MetricResponse:
    fmt = "!H"
    msgs = {
        Status.ok: "Ok!",
        Status.server_error: "Server error",
        Status.server_unavailable: "Server unavailable",
    }

    def __init__(self, status: Status):
        self.status = status

    @property
    def msg(self) -> str:
        return MetricResponse.msgs[self.status]

    @property
    def error(self) -> bool:
        return self.status in (Status.server_error, Status.server_unavailable)

    def to_bytes(self):
        return struct.pack(MetricResponse.fmt, self.status.value)

    @classmethod
    def from_bytes(cls, buffer):
        (status,) = struct.unpack(MetricResponse.fmt, buffer)
        return MetricResponse(status)

    def __str__(self):
        return f"metric response: {self.msg}"
