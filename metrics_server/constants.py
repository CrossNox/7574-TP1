import pathlib
from enum import Enum


class Aggregation(Enum):
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "cnt"


class Ramp(Enum):
    constant = "constant"
    linear = "linear"
    exponential = "exponential"


DEFAULT_PORT: int = 5678
DEFAULT_HOST: str = "localhost"
DEFAULT_WORKERS: int = 16
DEFAULT_BACKLOG: int = 10
DEFAULT_WRITERS: int = 10
DEFAULT_DATA_PATH: pathlib.Path = pathlib.Path("/tmp")
