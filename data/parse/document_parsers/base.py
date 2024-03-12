from abc import ABC, abstractmethod


class BaseDocumentParser(ABC):

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def parse(self, filename: str) -> str:
        pass
