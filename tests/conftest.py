from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest


class UploadedBytes(BytesIO):
    def __init__(self, content: str, name: str = "crawl.csv") -> None:
        super().__init__(content.encode("utf-8"))
        self.name = name

    def getvalue(self) -> bytes:  # type: ignore[override]
        position = self.tell()
        self.seek(0)
        value = super().getvalue()
        self.seek(position)
        return value


@pytest.fixture
def uploaded_bytes_factory():
    return UploadedBytes


@pytest.fixture
def core_screaming_frog_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Address": "https://example.com/a",
                "Content Type": "text/html; charset=utf-8",
                "Status Code": 200,
                "Indexability": "Indexable",
                "Title 1": "",
                "H1-1": "Page A",
                "Meta Description 1": "Shared meta",
                "Canonical Link Element 1": "https://example.com/a",
            },
            {
                "Address": "https://example.com/b",
                "Content Type": "text/html; charset=utf-8",
                "Status Code": 404,
                "Indexability": "Indexable",
                "Title 1": "Shared title",
                "H1-1": "",
                "Meta Description 1": "",
                "Canonical Link Element 1": "https://example.com/b",
            },
            {
                "Address": "https://example.com/c",
                "Content Type": "text/html; charset=utf-8",
                "Status Code": 200,
                "Indexability": "Indexable",
                "Title 1": "Shared title",
                "H1-1": "Page C",
                "Meta Description 1": "Shared meta",
                "Canonical Link Element 1": "",
            },
            {
                "Address": "https://example.com/d",
                "Content Type": "text/html; charset=utf-8",
                "Status Code": 200,
                "Indexability": "Indexable",
                "Title 1": "Unique D",
                "H1-1": "Page D",
                "Meta Description 1": "Unique D meta",
                "Canonical Link Element 1": "https://example.com/d",
            },
            {
                "Address": "https://example.com/e",
                "Content Type": "text/html; charset=utf-8",
                "Status Code": 200,
                "Indexability": "Indexable",
                "Title 1": "Unique E",
                "H1-1": "Page E",
                "Meta Description 1": "Unique E meta",
                "Canonical Link Element 1": "https://example.com/e",
            },
        ]
    )
