import csv
import dataclasses
import datetime
import json
from functools import cached_property
from typing import Any, Iterator

import bs4
from progress.bar import Bar

from data.parse.base import T
from data.parse.cbr.base import BaseCBRParser, Document


class BasicStandardsParser(BaseCBRParser):
    DATE_FORMAT = '%d.%m.%Y'
    FROM = 'basic_standard'

    def proceed_item(self, tag: bs4.Tag) -> Document:
        tds = tag.select('td')
        fin_org_type, title, _date1, _date2, protocol_number, publication_date, _date3, _redaction = tds
        url = title.select_one('a')['href']
        url = self.get_full_url(url)
        text, meta = self.fetch_pdf_document_text(url)
        doc = Document(url=self.prepare_url(url),
                       text=text.strip(),
                       title=self.extract_text(title),
                       date=datetime.datetime.strptime(self.extract_text(publication_date), self.DATE_FORMAT).date(),
                       name=self.extract_text(protocol_number),
                       source=self.extract_text(fin_org_type),
                       metadata=json.dumps(self.extend_metadata(meta)),
                       )
        self._progress_bar.next()
        return doc

    def proceed(self) -> Iterator[T]:
        for item in self.page.select('div.table > table > tbody > tr'):
            yield self.proceed_item(item)
        self._progress_bar.finish()

    @property
    def total_items(self) -> int:
        tag = self.page.select_one('div.table-wrapper > div.table-caption')
        return int(tag.text.rsplit(' ', 1)[1])

    @property
    def params(self) -> dict[str, Any]:
        return {
            'UniDbQuery.Posted': True,
            'UniDbQuery.vid': -1,
            'UniDbQuery.vidBS': -1,
            'UniDbQuery.redact': 1,
            'UniDbQuery.From': datetime.date(2001, 1, 1).strftime(self.DATE_FORMAT),
            'UniDbQuery.To': datetime.date.today().strftime(self.DATE_FORMAT),
        }

    @cached_property
    def page(self) -> bs4.BeautifulSoup:
        r = self.request(self.get_full_url('na/basic_standards'), params=self.params)
        return bs4.BeautifulSoup(r.content, 'html.parser')


def main() -> None:
    parser = BasicStandardsParser(Bar)
    with open('basic_standards.csv', 'w') as fd:
        writer = csv.writer(fd)
        for doc in parser.proceed():
            writer.writerow(dataclasses.astuple(doc))


if __name__ == '__main__':
    main()
