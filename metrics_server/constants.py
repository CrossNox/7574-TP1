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
