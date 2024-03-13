import argparse
import csv
import dataclasses
import datetime
import json
import logging
import re
from collections.abc import Iterator
from functools import cached_property
from typing import Any

import bs4
from progress.bar import Bar

from data.parse.cbr.base import BaseCBRParser, Document


class LegalActsParser(BaseCBRParser):
    DATE_NUMBER_REGEXP = re.compile(r'No (?P<name>.+)\nот (?P<dd>\d{2})\.(?P<mm>\d{2})\.(?P<yyyy>\d{4})')

    @cached_property
    def _initial_page(self) -> bs4.BeautifulSoup:
        r = self.request(self.get_full_url('na'))

        return bs4.BeautifulSoup(r.content, 'html.parser')

    @property
    def page_base_url(self) -> str:
        next_button = self._initial_page.select_one('#la_load')
        return next_button['data-cross-ajax-url'].split('?', 1)[0]

    @property
    def page_size(self) -> int:
        return len(self._initial_page.select('#content > div > div > div > div.cross-results > div.cross-result'))

    @property
    def total_items(self) -> int:
        text = self.extract_text(self._initial_page.select_one('div.results div.results_counter'))
        return int(text.split(' ', 1)[0]) - self._start_from_idx

    @property
    def total_pages(self) -> int:
        return (self.total_items + self.page_size - 1) // self.page_size

    @property
    def _start_page_idx(self) -> int:
        return self._start_from_idx // self.page_size

    @staticmethod
    def _get_params_for_page(page_idx: int) -> dict[str, Any]:
        return {
            'Date.Time': 'Any',
            'Page': page_idx,
        }

    def proceed_page(self, page_idx: int) -> Iterator[Document]:
        r = self.request(self.get_full_url(self.page_base_url), params=self._get_params_for_page(page_idx))

        soup = bs4.BeautifulSoup(r.content, 'html.parser')
        results_list = soup.select('div.cross-result')
        if self._start_page_idx == page_idx:
            results_list = results_list[self._start_from_idx % self.page_size:]

        for cross_result in results_list:
            yield self.proceed_item(cross_result)

    def proceed_item(self, tag: bs4.Tag) -> Document:
        date_number = self.DATE_NUMBER_REGEXP.fullmatch(self.extract_text(tag.select_one('.date-number')))
        title = tag.select_one('div.title-source > div.title a')
        url = title['href']
        source = tag.select_one('div.title-source > div.source')
        try:
            text, metadata = self.fetch_document_text(url)
            text = text.strip()
        except Exception as e:  # noqa
            logging.error(e)
            text, metadata = None, None
        if not url.lower().startswith('http'):
            url = self.get_full_url(url)
        doc = Document(
            url=url,
            text=text,
            title=self.extract_text(title),
            date=datetime.date(int(date_number['yyyy']), int(date_number['mm']), int(date_number['dd'])),
            source=self.extract_text(source),
            name=date_number['name'],
            metadata=json.dumps(metadata or {}),
        )
        self._progress_bar.next()
        return doc

    def proceed(self) -> Iterator[Document]:
        for page_idx in range(self._start_page_idx, self._start_page_idx + self.total_pages):
            yield from self.proceed_page(page_idx)
        self._progress_bar.finish()


def main():
    print(f'Скрипт запущен в {datetime.datetime.now()}')
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--start-from-idx', type=int, default=0)
    args = arg_parser.parse_args()

    parser = LegalActsParser(Bar, args.start_from_idx)
    with open('legal_acts_extra.csv', 'a') as fd:
        writer = csv.writer(fd)
        for doc in parser.proceed():
            writer.writerow(dataclasses.astuple(doc))


if __name__ == '__main__':
    main()
