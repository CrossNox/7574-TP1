import glob
import struct
import pathlib
import multiprocessing
from datetime import datetime
from typing import List, Optional

import pandas as pd

from metrics_server.constants import Status, Aggregation
from metrics_server.exceptions import EmptyAggregationArray
from metrics_server.utils import get_logger, minute_partition
from metrics_server.protocol import Query, QueryPartialResponse

logger = get_logger(__name__)


def handle_queries(queries_conns_queue: multiprocessing.Queue, data_path: pathlib.Path):
    try:
        while True:
            sock, addr = queries_conns_queue.get()
            buffer = sock.recv(struct.calcsize(Query.fmt))

            query = Query.from_bytes(buffer)
            logger.info("query: %s from %s", query, addr)

            try:
                agg = agg_metrics(
                    data_path,
                    query.metric,
                    query.agg,
                    query.agg_window,
                    query.start,
                    query.end,
                )

                logger.info("Got %s metrics to send", len(agg))

                for idx, value in enumerate(agg):
                    is_last = idx == (len(agg) - 1)
                    partial_response = QueryPartialResponse(Status.ok, value, is_last)
                    sock.sendall(partial_response.to_bytes())

            except EmptyAggregationArray:
                partial_response = QueryPartialResponse.emtpy()
                sock.sendall(partial_response.to_bytes())

            finally:
                sock.close()

    except ConnectionResetError:
        logger.info("Client closed connection before I could respond")
    except OSError:
        logger.info("Error while reading socket")
    except KeyboardInterrupt:
        logger.info("Got keyboard interrupt")
    except:  # pylint: disable=bare-except
        logger.error("Got unknown exception", exc_info=True)
    finally:
        logger.info("Exiting")
        try:
            sock.close()
        except UnboundLocalError:
            pass


def agg_metrics(
    data_path: pathlib.Path,
    metric: str,
    agg: Aggregation,
    agg_window: float,
    start: Optional[datetime],
    end: Optional[datetime],
) -> List[float]:
    dfs = []

    for partition in glob.glob(str(data_path / metric / "*")):
        filename = pathlib.Path(partition)

        if start is not None and int(filename.name) < minute_partition(
            start.timestamp()
        ):
            continue

        if end is not None and int(filename.name) > minute_partition(end.timestamp()):
            continue

        df = pd.read_csv(filename, names=["ts", "metric", "value"], engine="c")
        df.ts = df.ts.apply(datetime.fromtimestamp)

        if start is not None:
            df = df[df.ts >= start]

        if end is not None:
            df = df[df.ts <= end]

        dfs.append(df)

    if len(dfs) == 0:
        raise EmptyAggregationArray()

    df = pd.concat(dfs)

    if len(df) == 0:
        raise EmptyAggregationArray()

    df.sort_values("ts", inplace=True, ascending=True)

    if agg_window == 0.0:
        return df.value.tolist()

    df["offset"] = (df.ts - df.ts.iloc[0]).dt.total_seconds() // agg_window

    return df.groupby("offset").value.agg(agg.value).values.tolist()