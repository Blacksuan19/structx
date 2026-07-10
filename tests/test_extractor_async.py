import asyncio

from structx.extraction.extractor import Extractor
from structx.extraction.processors.data_processor import DataProcessor


class DummyExtractor:
    data_processor = DataProcessor()

    def extract(
        self,
        *,
        data,
        query,
        model=None,
        return_df=False,
        expand_nested=False,
        **kwargs,
    ):
        return {
            "data": data,
            "query": query,
            "model": model,
            "return_df": return_df,
            "expand_nested": expand_nested,
            "kwargs": kwargs,
        }

    def extract_queries(
        self,
        *,
        data,
        queries,
        return_df=True,
        expand_nested=False,
        **kwargs,
    ):
        return {
            "data": data,
            "queries": queries,
            "return_df": return_df,
            "expand_nested": expand_nested,
            "kwargs": kwargs,
        }

    def get_schema(self, *, data, query, **kwargs):
        return {"data": data, "query": query, "kwargs": kwargs}


DummyExtractor.extract_async = Extractor.extract_async
DummyExtractor.extract_queries_async = Extractor.extract_queries_async
DummyExtractor.get_schema_async = Extractor.get_schema_async


def test_extract_async_forwards_keyword_arguments():
    async def run():
        return await DummyExtractor().extract_async(
            data="data",
            query="query",
            model="model",
            return_df=True,
            expand_nested=True,
            option=1,
        )

    result = asyncio.run(run())

    assert result == {
        "data": "data",
        "query": "query",
        "model": "model",
        "return_df": True,
        "expand_nested": True,
        "kwargs": {"option": 1},
    }


def test_extract_queries_async_forwards_keyword_arguments():
    async def run():
        return await DummyExtractor().extract_queries_async(
            data="data",
            queries=["one", "two"],
            return_df=False,
            expand_nested=True,
            option=2,
        )

    result = asyncio.run(run())

    assert result == {
        "data": "data",
        "queries": ["one", "two"],
        "return_df": False,
        "expand_nested": True,
        "kwargs": {"option": 2},
    }


def test_get_schema_async_forwards_keyword_arguments():
    async def run():
        return await DummyExtractor().get_schema_async(
            data="data",
            query="query",
            option=3,
        )

    result = asyncio.run(run())

    assert result == {"data": "data", "query": "query", "kwargs": {"option": 3}}
