import pathlib
from enum import Enum


class Intent(Enum):
    metric = 1
    query = 2


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
DEFAULT_BACKLOG: int = 10
DEFAULT_WRITERS: int = 10
DEFAULT_QUERIERS: int = 2
DEFAULT_DATA_PATH: pathlib.Path = pathlib.Path("/tmp")
