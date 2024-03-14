import html
import tempfile
import unicodedata
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any, Generic, Iterator, Protocol, TypeVar

import bs4
import requests
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential, retry_if_exception

from data.parse.document_parsers.pdf.base import BasePDFParser


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

    def __init__(self, progress: type[ProgressProtocol] = DummyProgressBar, start_from_idx: int = 0):
        self._progress_class = progress
        self._start_from_idx = start_from_idx

    @cached_property
    def _progress_bar(self) -> ProgressProtocol:
        return self._progress_class(self.PROGRESS_BAR_NAME, max=self.total_items)

    def get_full_url(self, path: str) -> str:
        path = path.strip('/')
        return f'{self.BASE_URL}/{path}/'

    @retry(retry=retry_if_exception_type(PdfReadError),
           stop=stop_after_attempt(5),
           reraise=True,
           )
    def fetch_pdf_document_text(self, url: str, params: dict[str, Any] | None = None) -> tuple[str, dict[str, str]]:
        r = self.request(url, params=params)

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf') as fd:
            fd.write(r.content)
            reader = PdfReader(fd.name)
            metadata = {k.strip('/'): v for k, v in reader.metadata.items()}
            if self._is_pdf_scanned(reader):
                metadata['type'] = 'pdf/scanned'
                return self.ocr_pdf_parser.parse(fd.name), metadata
            else:
                text = ''
                for page in reader.pages:
                    text += page.extract_text()
                metadata['type'] = 'pdf/text'
                return text, metadata

    @staticmethod
    def _is_pdf_scanned(pdf: PdfReader) -> bool:
        """Проверяет, является ли документ отсканированным, т.е. не содержит текстовых данных, а только графические"""
        producer = 'paper' in pdf.metadata.get('/Producer', '').lower()
        creator = any(item in pdf.metadata.get('/Creator', '').lower() for item in ('canon', 'xerox'))
        return any((producer, creator))

    @cached_property
    @abstractmethod
    def ocr_pdf_parser(self) -> BasePDFParser:
        pass

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

    @retry(retry=retry_if_exception(lambda e: getattr(e, 'response', None) and
                                              (e.response.status_code in (401, 403) or
                                               e.response.status_code >= 500)),
           wait=wait_random_exponential(max=60),
           stop=stop_after_attempt(5),
           reraise=True,
           )
    def request(self, url: str, params: dict[str, Any] | None = None) -> requests.Response:
        r = self.__session.get(url, params=params, timeout=120)
        r.raise_for_status()
        return r

    @cached_property
    def __session(self) -> requests.Session:
        return requests.session()

    @staticmethod
    def prepare_url(url: str) -> str:
        if not url.endswith('/'):
            url += '/'
        url = url.replace('//www.', '//')
        return url