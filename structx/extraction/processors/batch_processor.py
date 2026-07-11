"""Bounded concurrent mapping of prepared DataFrame rows."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, List

from tqdm import tqdm

from structx.core.input import PreparedInput, RowPayload

RowWorker = Callable[[RowPayload, int, Any], Any]
AsyncRowWorker = Callable[[RowPayload, int, Any], Awaitable[Any]]


class BatchProcessor:
    """Serialize rows and execute a worker with bounded concurrency."""

    def __init__(self, max_threads: int = 10, batch_size: int = 100) -> None:
        if (
            not isinstance(max_threads, int)
            or isinstance(max_threads, bool)
            or max_threads < 1
        ):
            raise ValueError("max_threads must be a positive integer")
        if (
            not isinstance(batch_size, int)
            or isinstance(batch_size, bool)
            or batch_size < 1
        ):
            raise ValueError("batch_size must be a positive integer")
        self.max_threads = max_threads
        self.batch_size = batch_size

    def map_rows(
        self,
        prepared_input: PreparedInput,
        worker: RowWorker,
        target_columns: List[str],
    ) -> List[Any]:
        """Process all rows in stable input order and bounded batches."""
        results: List[Any] = []
        dataframe = prepared_input.dataframe
        for batch_start in range(0, len(dataframe), self.batch_size):
            batch = dataframe.iloc[batch_start : batch_start + self.batch_size]
            results.extend(
                self._map_batch(
                    prepared_input, batch_start, len(batch), worker, target_columns
                )
            )
        return results

    async def map_rows_async(
        self,
        prepared_input: PreparedInput,
        worker: AsyncRowWorker,
        target_columns: List[str],
    ) -> List[Any]:
        """Asynchronously process rows with stable ordering and bounded concurrency."""
        results: List[Any] = []
        semaphore = asyncio.Semaphore(self.max_threads)
        dataframe = prepared_input.dataframe
        for batch_start in range(0, len(dataframe), self.batch_size):
            batch_length = len(
                dataframe.iloc[batch_start : batch_start + self.batch_size]
            )
            results.extend(
                await self._map_batch_async(
                    prepared_input,
                    batch_start,
                    batch_length,
                    worker,
                    target_columns,
                    semaphore,
                )
            )
        return results

    async def _map_batch_async(
        self,
        prepared_input: PreparedInput,
        start_position: int,
        batch_length: int,
        worker: AsyncRowWorker,
        target_columns: List[str],
        semaphore: asyncio.Semaphore,
    ) -> List[Any]:
        batch = prepared_input.dataframe.iloc[
            start_position : start_position + batch_length
        ]
        row_tasks = [
            (
                prepared_input.row_payload(
                    start_position + offset, row, target_columns
                ),
                start_position + offset,
                label,
            )
            for offset, (label, row) in enumerate(batch.iterrows())
        ]

        async def run(index: int, task: tuple[RowPayload, int, Any]):
            async with semaphore:
                return index, await worker(*task)

        tasks = [
            asyncio.create_task(run(index, task))
            for index, task in enumerate(row_tasks)
        ]
        ordered: List[Any] = [None] * len(tasks)
        try:
            with tqdm(
                total=len(tasks), desc="Processing batch", unit="row"
            ) as progress:
                for completed in asyncio.as_completed(tasks):
                    index, result = await completed
                    ordered[index] = result
                    progress.update(1)
        finally:
            pending = []
            for task in tasks:
                if not task.done():
                    task.cancel()
                    pending.append(task)
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        return ordered

    def _map_batch(
        self,
        prepared_input: PreparedInput,
        start_position: int,
        batch_length: int,
        worker: RowWorker,
        target_columns: List[str],
    ) -> List[Any]:
        batch = prepared_input.dataframe.iloc[
            start_position : start_position + batch_length
        ]
        tasks = [
            (
                prepared_input.row_payload(
                    start_position + offset, row, target_columns
                ),
                start_position + offset,
                label,
            )
            for offset, (label, row) in enumerate(batch.iterrows())
        ]
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = [executor.submit(worker, *task) for task in tasks]
            return [
                future.result()
                for future in tqdm(
                    futures,
                    desc="Processing batch",
                    unit="row",
                    total=len(futures),
                )
            ]
