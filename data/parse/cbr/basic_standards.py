import dataclasses
import datetime
from functools import cached_property
from typing import Any, Iterator

import bs4
from progress.bar import Bar

from data.parse.base import T
from data.parse.cbr.base import BaseCBRParser


@dataclasses.dataclass
class Document:
    organization_type: str
    basic_standard_type: str
    name: str
    date: datetime.date  # дата начала применения
    protocol_uid: str


class BasicStandardsParser(BaseCBRParser[Document]):
    DATE_FORMAT = '%d.%m.%Y'

    def proceed_item(self, tag: bs4.Tag) -> Document:
        tds = tag.select('td')
        name = self.extract_text(tds[1])
        url = tds[1]['href']
        self._progress_bar.next()

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
    print(parser.total_items)


if __name__ == '__main__':
    main()
