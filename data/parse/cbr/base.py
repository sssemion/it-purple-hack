import dataclasses
import re
from abc import ABC
from typing import Any
from urllib.parse import parse_qs

import bs4

from data.parse.base import BaseParser


@dataclasses.dataclass
class Document:
    url: str
    text: str | None


class BaseCBRParser(BaseParser[Document], ABC):
    BASE_URL = 'https://cbr.ru'
    PUBLICATION_PRAVO_GOV_RU_REGEXP = re.compile(r'https?://publication\.pravo\.gov\.ru/[Dd]ocument/([Vv]iew/)?(?P<doc_uid>\d+)/?')
    PUBLICATION_PRAVO_GOV_RU_TEXT_URL = 'http://actual.pravo.gov.ru/text.html'

    PRAVO_GOV_RU_REGEXP = re.compile(r'https?://pravo\.gov\.ru/proxy/ips/\?(?P<url_qs>.+)/?')
    PRAVO_GOV_RU_TEXT_URL = 'http://pravo.gov.ru/proxy/ips/'
    PRAVO_GOV_RU_TEXT_PARAMS = {'doc_itself': '', 'nd': None}

    def fetch_document_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        if match := self.PUBLICATION_PRAVO_GOV_RU_REGEXP.fullmatch(url):
            r = self.request(self.PUBLICATION_PRAVO_GOV_RU_TEXT_URL + f'#pnum={match["doc_uid"]}', params)
            soup = bs4.BeautifulSoup(r.content, 'html.parser')
            return self.extract_text(soup.select_one('iframe.doc-body'))
        elif match := self.PRAVO_GOV_RU_REGEXP.fullmatch(url):
            params = params or {}
            params.update(self.PRAVO_GOV_RU_TEXT_PARAMS)
            params['nd'] = parse_qs(match['url_qs'])['nd'][0]
            soup = bs4.BeautifulSoup(self.request(self.PRAVO_GOV_RU_TEXT_URL, params).content, 'html.parser')
            return self.extract_text(soup.select_one('#text_content'))
        elif url.startswith('http://') or url.startswith('https://'):
            return self.fetch_pdf_document_text(url, params)
        return self.fetch_pdf_document_text(self.get_full_url(url), params)
