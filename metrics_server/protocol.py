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
    empty = 4
    does_not_exist = 5
    bad_format = 6


class ProtocolMessage(abc.ABC):
    """Abstract class of classes to be sent over binary protocol."""

    fmt = ""

    @abc.abstractmethod
    def to_bytes(self):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, buffer):
        raise NotImplementedError()


class ProtocolResponseMessage(ProtocolMessage, abc.ABC):
    """Abstract class of response classes to be sent over binary protocol."""

    msgs = {
        Status.ok: "Ok!",
        Status.server_error: "Server error",
        Status.server_unavailable: "Server unavailable",
        Status.empty: "Metric is empty",
        Status.does_not_exist: "Metric does not exist",
        Status.bad_format: "Bad format",
    }

    def __init__(self, status):
        self.status = status

    @property
    def error(self) -> bool:
        return self.status != Status.ok

    @property
    def msg(self) -> str:
        return self.msgs[self.status]


class IntentionPackage(ProtocolMessage):
    """Declaration of intention."""

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
    """Metric to send."""

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
    """Query to send."""

    fmt = "!28p12pddd"

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
        start_ts = self.start.timestamp() if self.start is not None else -1
        end_ts = self.end.timestamp() if self.end is not None else -1
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


class QueryPartialResponse(ProtocolResponseMessage):
    """Partial response sent to answer a query."""

    fmt = "!Hf?"

    def __init__(self, status: Status, aggvalue: float, last: bool):
        super().__init__(status)
        self.aggvalue = aggvalue
        self.last = last

    @classmethod
    def empty(cls):
        return QueryPartialResponse(Status.empty, 0, True)

    @classmethod
    def not_exist(cls):
        return QueryPartialResponse(Status.does_not_exist, 0, True)

    @classmethod
    def bad_format(cls):
        return QueryPartialResponse(Status.bad_format, 0, True)

    @classmethod
    def server_unavailable(cls):
        return QueryPartialResponse(Status.server_unavailable, 0, True)

    @property
    def is_empty(self):
        return self.status == Status.empty

    def to_bytes(self):
        return struct.pack(
            QueryPartialResponse.fmt, self.status.value, self.aggvalue, self.last
        )

    @classmethod
    def from_bytes(cls, buffer):
        status, aggvalue, last = struct.unpack(QueryPartialResponse.fmt, buffer)
        return QueryPartialResponse(Status(status), aggvalue, last)


class ReceivedMetric(ProtocolMessage):
    """Metric received by the server."""

    fmt = "!28pdf"

    def __init__(self, identifier: str, value: int, ts: Optional[float] = None):
        self.identifier = identifier
        self.value = value
        if ts is None:
            self.timestamp = time.time()
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


class NotificationResponse(ProtocolResponseMessage):
    """Notification data to send to monitoring clients."""

    fmt = "!d128p?H"

    def __init__(
        self, dt: datetime, msg: str, stopping: bool = False, status: Status = Status.ok
    ):
        super().__init__(status)
        self.dt = dt
        self.message = msg
        self.stopping = stopping

    def to_bytes(self):
        return struct.pack(
            NotificationResponse.fmt,
            self.dt.timestamp(),
            self.message.encode(),
            self.stopping,
            self.status.value,
        )

    @classmethod
    def from_bytes(cls, buffer):
        (dt, msg, stopping, status) = struct.unpack(NotificationResponse.fmt, buffer)
        return NotificationResponse(
            datetime.fromtimestamp(dt), msg.decode(), stopping, Status(status)
        )

    @classmethod
    def server_unavailable(cls):
        return NotificationResponse(datetime.now(), "", Status.server_unavailable)


class MetricResponse(ProtocolResponseMessage):
    """Response to a received metric."""

    fmt = "!H"

    @classmethod
    def bad_format(cls):
        return MetricResponse(Status.bad_format)

    @classmethod
    def server_unavailable(cls):
        return MetricResponse(Status.server_unavailable)

    def to_bytes(self):
        return struct.pack(MetricResponse.fmt, self.status.value)

    @classmethod
    def from_bytes(cls, buffer):
        (status,) = struct.unpack(MetricResponse.fmt, buffer)
        return MetricResponse(Status(status))

    def __str__(self):
        return f"metric response: {self.msg}"
