import pathlib
from enum import Enum


class Intent(Enum):
    metric = 1
    query = 2
    monitor = 3


class Aggregation(Enum):
    AVG = "mean"
    MIN = "min"
    MAX = "max"
    COUNT = "count"


class Ramp(Enum):
    constant = "constant"
    linear = "linear"
    exponential = "exponential"


DEFAULT_PORT: int = 5678
DEFAULT_HOST: str = "localhost"
DEFAULT_WORKERS: int = 16
DEFAULT_BACKLOG: int = 8
DEFAULT_WRITERS: int = 16
DEFAULT_QUERIERS: int = 4
DEFAULT_NOTIFIERS: int = 4
DEFAULT_DATA_PATH: pathlib.Path = pathlib.Path("/tmp")
DEFAULT_NOTIFICATIONS_LOG_PATH: pathlib.Path = pathlib.Path(
    "/tmp/metrics_server_notifications.log"
)
DEFAULT_NOTIFICATIONS_FILE: pathlib.Path = (
    pathlib.Path(__file__).parent.parent / "notifications.ini"
)
