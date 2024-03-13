import dataclasses
import json
import re
from abc import ABC
from datetime import datetime, date
from functools import cached_property
from typing import Any
from urllib.parse import parse_qs

import bs4

from data.parse.base import BaseParser
from data.parse.document_parsers.pdf.base import BasePDFParser
from data.parse.document_parsers.pdf.tesseract import TesseractPDFParser


@dataclasses.dataclass
class Document:
    url: str
    text: str | None
    title: str | None
    date: date | None
    name: str | None  # идентификатор документа вида ФЗ-1234
    source: str | None  # что-то вроде типа документа ("Информационное письмо", "Федеральный закон" итд)
    metadata: str  # json dump < dict[str, str] >


class BaseCBRParser(BaseParser[Document], ABC):
    BASE_URL = 'https://cbr.ru'
    PUBLICATION_PRAVO_GOV_RU_REGEXP = re.compile(r'https?://publication\.pravo\.gov\.ru/[Dd]ocument/([Vv]iew/)?(?P<doc_uid>\d+)/?')
    PUBLICATION_PRAVO_GOV_RU_TEXT_URL = 'http://actual.pravo.gov.ru/text.html'

    PRAVO_GOV_RU_REGEXP = re.compile(r'https?://pravo\.gov\.ru/proxy/ips/\?(?P<url_qs>.+)/?')
    PRAVO_GOV_RU_TEXT_URL = 'http://pravo.gov.ru/proxy/ips/'
    PRAVO_GOV_RU_TEXT_PARAMS = {'doc_itself': '', 'nd': None}

    def fetch_document_text(self, url: str, params: dict[str, Any] | None = None) -> tuple[str, dict[str, str]]:  # returns text and metadata  # noqa
        if match := self.PUBLICATION_PRAVO_GOV_RU_REGEXP.fullmatch(url):
            redactions = self.request('http://actual.pravo.gov.ru:8000/api/ebpi/redactions', params={'t': json.dumps({'pnum': match['doc_uid']})})
            red_id = max(redactions.json()['redactions'], key=lambda x: datetime.fromisoformat(x['RedDateTimeD']))['RedId']
            r = self.request('http://actual.pravo.gov.ru:8000/api/ebpi/redtext', params={'t': red_id})
            soup = bs4.BeautifulSoup(r.json()['RedText'], 'html.parser')
            return self.extract_text(soup.select_one('body')), {'type': 'plain_text'}
        elif match := self.PRAVO_GOV_RU_REGEXP.fullmatch(url):
            params = params or {}
            params.update(self.PRAVO_GOV_RU_TEXT_PARAMS)
            params['nd'] = parse_qs(match['url_qs'])['nd'][0]
            soup = bs4.BeautifulSoup(self.request(self.PRAVO_GOV_RU_TEXT_URL, params).content, 'html.parser')
            for title in soup.select('title'):
                if title.text == 'Complex':
                    title.replace_with('')
            for style in soup.select('style'):
                style.replace_with('')
            for script in soup.select('script'):
                script.replace_with('')
            return self.extract_text(soup.select_one('#text_content')), {'type': 'plain_text'}
        elif url.startswith('http://') or url.startswith('https://'):
            return self.fetch_pdf_document_text(url, params=params)
        return self.fetch_pdf_document_text(self.get_full_url(url), params=params)

    @cached_property
    def ocr_pdf_parser(self) -> BasePDFParser:
        return TesseractPDFParser('rus')
