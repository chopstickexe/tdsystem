import datetime
import re
import urllib.request
from collections import namedtuple
from enum import Enum
from typing import Dict, List

from bs4 import BeautifulSoup
from bs4.element import Tag

from parser_base import Parser


class Course(Enum):
    SHORT = '25m'
    LONG = '50m'


class Meet:
    def __init__(self,
                 dates: List[datetime.date] = None,
                 name: str = None,
                 course: Course = None,
                 venue: str = None,
                 q_params: Dict[str, str] = None):
        self.dates = dates
        self.name = name
        self.course = course
        self.venue = venue
        self.q_params = q_params

    def add_date(self, date: datetime.date):
        if not self.dates:
            self.dates = []
        self.dates.append(date)

    def add_q_param(self, key: str, val: str):
        if not self.q_params:
            self.q_params = {}
        self.q_params[key] = val

    def __str__(self):
        return 'name={}, dates={}, course={}, venue={}, q_params={}'.format(
            self.name, self.dates, self.course, self.venue, self.q_params)


class MonthPageParser(Parser):
    def __init__(self, page: Tag, year: int = 0, month: int = 0):
        self.year = year
        self.month = month
        self.page = page

    def __get_meet_query_params(self, form: Tag) -> Dict[str, str]:
        params = {}
        params['action'] = form.get('action')
        for input in form.find_all('input', attrs={'type': 'hidden'}):
            params[input.get('name')] = input.get('value')
        return params

    def get_available_years(self) -> List[str]:
        form = self.page.find('form', attrs={'name': 'SelectYear'})
        if not form:
            return None
        ys = []
        for yo in form.find_all('option', attrs={'name': 'SelYearList'}):
            ys.append(yo.get('value'))
        return ys

    SHORT_COURSE_PAT = re.compile(r'\((25m)\)')
    LONG_COURSE_PAT = re.compile(r'\((50m)\)')

    def get_meets(self) -> List[Meet]:
        form = self.page.find('form', attrs={'name': 'gamelist'})
        if not form:
            return None
        params = self.__get_meet_query_params(form)
        ms = []
        for tr in form.find_all('tr'):
            meet = Meet(q_params=params.copy())
            tds = tr.find_all('td')
            if len(tds) < 4:
                continue
            meet.dates = self.get_days(self.normalize(tds[0].get_text()))
            meet.name = self.normalize(tds[1].get_text())

            # Process venue
            venue_text = self.normalize(tds[2].get_text())
            m = self.__class__.SHORT_COURSE_PAT.search(venue_text)
            if m:
                meet.course = Course(m.group(1))
                meet.venue = venue_text[0:m.span()[0]]
            m = self.__class__.LONG_COURSE_PAT.search(venue_text)
            if m:
                meet.course = Course(m.group(1))
                meet.venue = venue_text[0:m.span()[0]]

            b = tds[3].find('button')
            if b:
                meet.add_q_param(b.get('name'), b.get('value'))

            ms.append(meet)
        return ms

    DATE_PAT = re.compile(r'([0-9]+)日\([日月火水木金土・祝]+\)')

    def get_days(self, days: str) -> List[datetime.datetime]:
        ret = []
        if not days:
            return None
        for m in self.__class__.DATE_PAT.finditer(days):
            ret.append(datetime.date(self.year, self.month, int(m.group(1))))
        return ret

    VenueInfo = namedtuple('VenueInfo', ('name', 'COURSE'))

    def process_venue(self, venue_text: str) -> VenueInfo:
        m = self.__class__.SHORT_COURSE_PAT.search(venue_text)
        if m:
            return self.__class__.VenueInfo(
                name=venue_text[0:m.span()[0]], course='short')

        m = self.__class__.LONG_COURSE_PAT.search(venue_text)
        if m:
            return self.__class__.VenueInfo(
                name=venue_text[0:m.span()[0]], course='long')

        return self.__class__.VenueInfo(name=venue_text)


if __name__ == '__main__':
    req = urllib.request.Request('{}?{}'.format(
        'http://www.tdsystem.co.jp/',
        urllib.parse.urlencode({
            'Y': '2018',
            'M': '08'
        })))
    with urllib.request.urlopen(req) as res:
        page = BeautifulSoup(res, 'lxml')
        p = MonthPageParser(year=2018, month=8, page=page)
        ms = p.get_meets()
        for m in ms:
            print(m)
