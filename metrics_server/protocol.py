import abc
import time
import struct
from enum import Enum
from typing import Optional
from datetime import datetime

from metrics_server.constants import Intent, Aggregation


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


class IntentionPackage(ProtocolMessage):
    fmt = "!i"

    def __init__(self, intent: Intent):
        self.intent = intent

    def to_bytes(self):
        return struct.pack(IntentionPackage.fmt, self.intent.value)

    @classmethod
    def from_bytes(cls, buffer):
        (intent,) = struct.unpack(IntentionPackage.fmt, buffer)
        return IntentionPackage(Intent(intent))


class Metric(ProtocolMessage):
    fmt = "!28pL"

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


class Query(ProtocolMessage):
    fmt = "!28p12pfff"

    def __init__(
        self,
        metric: str,
        agg: Aggregation,
        agg_window: float,
        start: Optional[datetime],
        end: Optional[datetime],
    ):
        self.metric = metric
        self.agg = agg
        self.agg_window = agg_window
        self.start = start
        self.end = end

    def to_bytes(self):
        start_ts = self.start if self.start is not None else -1
        end_ts = self.end if self.end is not None else -1
        return struct.pack(
            Query.fmt,
            self.metric.encode(),
            self.agg.value.encode(),
            self.agg_window,
            start_ts,
            end_ts,
        )

    @classmethod
    def from_bytes(self, buffer):
        metric, agg, agg_window, start_ts, end_ts = struct.unpack(Query.fmt, buffer)
        return Query(
            metric.decode(),
            Aggregation(agg.decode()),
            agg_window,
            datetime.fromtimestamp(start_ts) if start_ts > 0 else None,
            datetime.fromtimestamp(end_ts) if end_ts > 0 else None,
        )

    def __str__(self):
        return f"query {self.metric} aggregated by {self.agg} from {self.start} to {self.end} on a window of size {self.agg_window}"


class QueryPartialResponse(ProtocolMessage):
    fmt = "!Hf?"
    msgs = {
        Status.ok: "Ok!",
        Status.server_error: "Server error",
        Status.server_unavailable: "Server unavailable",
    }

    def __init__(self, status: Status, aggvalue: float, last: bool):
        self.status = status
        self.aggvalue = aggvalue
        self.last = last

    @property
    def msg(self) -> str:
        return QueryPartialResponse.msgs[self.status]

    @property
    def error(self) -> bool:
        return self.status in (Status.server_error, Status.server_unavailable)

    def to_bytes(self):
        return struct.pack(
            QueryPartialResponse.fmt, self.status.value, self.aggvalue, self.last
        )

    @classmethod
    def from_bytes(cls, buffer):
        status, aggvalue, last = struct.unpack(QueryPartialResponse.fmt, buffer)
        return QueryPartialResponse(Status(status), aggvalue, last)


class ReceivedMetric(ProtocolMessage):
    fmt = "!28pLf"

    def __init__(self, identifier: str, value: int, ts: Optional[int] = None):
        self.identifier = identifier
        self.value = value
        if ts is None:
            self.timestamp = int(time.time())
        else:
            self.timestamp = ts

    def to_bytes(self):
        return struct.pack(
            ReceivedMetric.fmt, self.identifier.encode(), self.value, self.timestamp
        )

    @classmethod
    def from_bytes(cls, buffer):
        identifier, value, ts = struct.unpack(ReceivedMetric.fmt, buffer)
        return ReceivedMetric(identifier.decode(), value, ts)

    def __str__(self):
        return f"received metric: {self.identifier} -> {self.value} @ {self.timestamp}"

    @classmethod
    def from_metric(cls, metric):
        return ReceivedMetric(metric.identifier, metric.value)


class MetricResponse(ProtocolMessage):
    fmt = "!H"
    # TODO: abstract into abstract class
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
        return MetricResponse(Status(status))

    def __str__(self):
        return f"metric response: {self.msg}"
