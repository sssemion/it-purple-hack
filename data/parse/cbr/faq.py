import csv
import dataclasses
import datetime
import json
import re
import warnings
from collections.abc import Iterator
from functools import cached_property

import bs4
from progress.bar import Bar

from data.parse.cbr.base import BaseCBRParser, Document


@dataclasses.dataclass
class Rubric:
    questions_count: int
    title: str
    url: str


class FaqParser(BaseCBRParser):

    DATE_REGEXP = re.compile(r'(?P<dd>\d{2})\.(?P<mm>\d{2})\.(?P<yyyy>\d{4})')
    INITIAL_PAGE_URL = 'faq'
    PROGRESS_BAR_NAME = 'FAQ Progress'
    FROM = 'faq'

    @cached_property
    def already_parsed(self) -> set[str]:
        return set()

    @cached_property
    def _initial_page(self) -> bs4.BeautifulSoup:
        r = self.request(self.get_full_url(self.INITIAL_PAGE_URL))

        return bs4.BeautifulSoup(r.content, 'html.parser')

    @cached_property
    def rubrics(self) -> list[Rubric]:
        result = []
        for tag in self._initial_page.select('.rubric-wrap .rubric'):
            stub = self.extract_text(tag.select_one('.rubric_sub')).strip()
            questions_count, *_ = stub.split(' ', 1)
            title_tag = tag.select_one('.rubric_title')
            result.append(Rubric(questions_count=int(questions_count), title=self.extract_text(title_tag), url=title_tag['href']))
        return result

    def _proceed_rubric(self, rubric: Rubric) -> Iterator[Document | None]:
        r = self.request(self.get_full_url(rubric.url))
        soup = bs4.BeautifulSoup(r.content, 'html.parser')

        for question in soup.select('.container-fluid > div > .dropdown.question'):
            yield self.proceed_item(question, rubric.title)
        for question in soup.select('.container-fluid > div > .title-container > .dropdown.question'):
            yield self.proceed_item(question, rubric.title)

        for dropdown_container in soup.select('.dropdown_container'):
            if title_link := dropdown_container.select_one('.dropdown_title-link'):
                a = title_link.select_one('a')
                url = a['href']
                title = self.extract_text(a)
                r = self.request(self.get_full_url(url))
                content = bs4.BeautifulSoup(r.content, 'html.parser')

            elif title_tag := dropdown_container.select_one('.dropdown_title'):
                title = self.extract_text(title_tag)
                content = dropdown_container.select_one('.dropdown_content')
            else:
                raise ValueError('Неопознанный dropdown')
            for dropdown_question in content.select('.dropdown.question'):
                yield self.proceed_item(dropdown_question, '. '.join([rubric.title, title]))

    @property
    def total_items(self) -> int:
        return sum(rubric.questions_count for rubric in self.rubrics)

    def proceed_item(self, tag: bs4.Tag, source: str = '') -> Document | None:
        title = self.extract_text(tag.select_one('.question_title'))
        content = tag.select_one('.dropdown_content')
        if content is None:
            warnings.warn(f'Invalid tag: {tag}')
            return None
        date_match = self.DATE_REGEXP.search(self.extract_text(content.select_one('.dropdown_date')))
        date = datetime.date(int(date_match['yyyy']), int(date_match['mm']), int(date_match['dd']))
        text = self.extract_text(content.select_one('.additional-text-block'))
        url = content.select_one('.copy-btn')['data-copy-url']
        doc = Document(
            url=self.prepare_url(url),
            text=text.strip(),
            title=title,
            date=date,
            name=None,
            source=source,
            metadata=json.dumps(self.extend_metadata({'type': 'plain_text'})),
        )
        return doc

    def proceed(self) -> Iterator[Document]:
        for rubric in self.rubrics:
            for doc in self._proceed_rubric(rubric):
                if doc and doc.url not in self.already_parsed:
                    self.already_parsed.add(doc.url)
                    self._progress_bar.next()
                    yield doc
        self._progress_bar.finish()


class ExplanParser(FaqParser):
    INITIAL_PAGE_URL = 'explan'
    PROGRESS_BAR_NAME = 'Explanation Progress'
    FROM = 'explan'


def main():
    print(f'Скрипт запущен в {datetime.datetime.now()}')

    parser = FaqParser(Bar)
    with open('faq.csv', 'w') as fd:
        writer = csv.writer(fd)
        for doc in parser.proceed():
            writer.writerow(dataclasses.astuple(doc))

    parser = ExplanParser(Bar)
    with open('explan.csv', 'w') as fd:
        writer = csv.writer(fd)
        for doc in parser.proceed():
            writer.writerow(dataclasses.astuple(doc))


if __name__ == '__main__':
    main()
