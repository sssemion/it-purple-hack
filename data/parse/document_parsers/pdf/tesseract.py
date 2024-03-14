from typing import Literal

import textract

from data.parse.document_parsers.pdf.base import BasePDFParser


class TesseractPDFParser(BasePDFParser):

    def __init__(self, language: Literal['eng', 'rus']):
        self.language = language

    def parse(self, filename: str) -> str:
        text = textract.process(filename, method='tesseract', language=self.language)
        return text.decode()
