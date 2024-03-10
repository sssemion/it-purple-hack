import html
import unicodedata
from abc import ABC, abstractmethod
from functools import cached_property
from io import BytesIO
from typing import Any, Generic, Iterator, Protocol, TypeVar

import bs4
import requests
from PyPDF2 import PdfReader


class BaseParseError(Exception):
    pass


T = TypeVar('T')


class ProgressProtocol(Protocol):
    def __init__(self, name: str, max: int, *args, **kwargs):
        pass

    def next(self) -> None:
        pass

    def finish(self) -> None:
        pass

    def __enter__(self) -> None:
        pass

    def __exit__(self, *args, **kwargs) -> None:
        pass


class DummyProgressBar(ProgressProtocol):
    pass


class BaseParser(ABC, Generic[T]):
    BASE_URL: str
    PROGRESS_BAR_NAME: str = 'Progress'

    def __init__(self, progress: type[ProgressProtocol] = DummyProgressBar):
        self._progress_class = progress

    @cached_property
    def _progress_bar(self) -> ProgressProtocol:
        return self._progress_class(self.PROGRESS_BAR_NAME, max=self.total_items)

    def get_full_url(self, path: str) -> str:
        path = path.strip('/')
        return f'{self.BASE_URL}/{path}/'

    def fetch_pdf_document_text(self, document_path: str) -> str:
        r = requests.get(self.get_full_url(document_path))
        r.raise_for_status()

        fd = BytesIO()
        fd.write(r.content)
        reader = PdfReader(fd)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
        return text

    @staticmethod
    def extract_text(tag: bs4.Tag) -> str:
        return unicodedata.normalize('NFKC', html.unescape(tag.text.strip()))

    @property
    @abstractmethod
    def total_items(self) -> int:
        pass

    @abstractmethod
    def proceed(self) -> Iterator[T]:
        pass

    @abstractmethod
    def proceed_item(self, tag: bs4.Tag) -> T:
        pass

    @staticmethod
    def request(url: str, params: dict[str, Any] | None = None) -> requests.Response:
        r = requests.get(url, params=params)
        r.raise_for_status()
        return r
