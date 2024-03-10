import dataclasses
from abc import ABC

from data.parse.base import BaseParser


@dataclasses.dataclass
class Document:
    url: str
    text: str


class BaseCBRParser(BaseParser[Document], ABC):
    BASE_URL = 'https://cbr.ru'
