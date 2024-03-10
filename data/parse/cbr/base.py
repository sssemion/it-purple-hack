from abc import ABC
from typing import Generic, TypeVar

from data.parse.base import BaseParser

T = TypeVar('T')


class BaseCBRParser(BaseParser, ABC, Generic[T]):
    BASE_URL = 'https://cbr.ru'
