import re
import urllib.request
from datetime import timedelta
from enum import Enum
from typing import Dict, List

from bs4 import BeautifulSoup
from bs4.element import Tag

from tdsystem.parser import Parser


class Record:
    def __init__(self,
                 rank: int = 0,
                 record: timedelta = None,
                 lap: List[timedelta] = None):
        self.rank = rank
        self.record = record
        self.lap = lap

    def __str__(self):
        ret = 'rank={}, record={}, lap=['.format(self.rank, str(self.record))
        l_txt = ''
        for l in self.lap:
            if len(l_txt) > 0:
                l_txt += ', '
            l_txt += str(l)
        ret += l_txt
        ret += ']'
        return ret

    def set_record(self, mins: int = 0, secs: int = 0,
                   one_tenth_secs: int = 0):
        self.record = timedelta(
            minutes=mins, seconds=secs, milliseconds=one_tenth_secs * 10)

    def add_lap(self, mins: int = 0, secs: int = 0, one_tenth_secs: int = 0):
        if not self.lap:
            self.lap = []
        self.lap.append(
            timedelta(
                minutes=mins, seconds=secs, milliseconds=one_tenth_secs * 10))


class RecordPageParser(Parser):
    def __init__(self, page: Tag):
        self.page = page

    def get_query_params(self) -> Dict[str, str]:
        form = self.page.find('form', attrs={'name': 'formclasslist'})
        if not form:
            return None
        params = {}
        for input in form.find_all('input', attrs={'type': 'hidden'}):
            params[input.get('name')] = input.get('value')
        return params

    def get_available_classes(self) -> Dict[str, str]:
        form = self.page.find('form', attrs={'name': 'formclasslist'})
        if not form:
            return None
        select = form.find('select')
        if not select:
            return None
        classes = {}
        for c in select.find_all('option'):
            value = c.get('value')
            if value == '999':  # Wildcard
                continue
            classes[value] = self.normalize(c.get_text())
        return classes

    def get_records(self) -> List[Record]:
        for t in self.page.find_all('table'):
            if not self.has_records(t):
                continue
            return self.__get_records(t)
        return None

    def has_records(self, table: Tag) -> bool:
        th = table.find('th')
        if th and th.get_text() == '順位':
            return True
        return False

    RECORD_PAT = re.compile(r'([0-9]{0,2}):{0,1}([0-9]{2}).([0-9]{2})')

    RowType = Enum('RowType', ('RECORD', 'LAP'))

    def __get_records(self, table: Tag) -> List[Record]:
        rs = []
        r = Record()
        for tr in table.find_all('tr', recursive=False):
            rt = self.__get_row_type(tr)
            if not rt:
                continue

            if rt == RecordPageParser.RowType.RECORD:
                for i, td in enumerate(tr.find_all('td')):
                    txt = self.normalize(td.get_text())
                    if not txt:
                        continue
                    if i == 0:
                        r.rank = int(txt)
                    m = RecordPageParser.RECORD_PAT.match(txt)
                    if not m:
                        continue
                    r.set_record(
                        mins=int(m.group(1)) if len(m.group(1)) > 0 else 0,
                        secs=int(m.group(2)),
                        one_tenth_secs=int(m.group(3)))
            elif rt == RecordPageParser.RowType.LAP:
                rt = tr.find('table')
                if not rt:
                    continue
                for td in rt.find_all('td'):
                    txt = self.normalize(td.get_text())
                    if not txt:
                        continue
                    m = RecordPageParser.RECORD_PAT.match(txt)
                    if not m:
                        continue
                    r.add_lap(
                        mins=int(m.group(1)) if len(m.group(1)) > 0 else 0,
                        secs=int(m.group(2)),
                        one_tenth_secs=int(m.group(3)))
                rs.append(r)
                r = Record()
        return rs

    def __get_row_type(self, tr: Tag) -> RowType:
        td = tr.find('td')  # Get 1st td
        if not td:
            return None
        txt = self.normalize(td.get_text())
        if txt and re.match('[0-9]+', txt):
            return self.__class__.RowType.RECORD
        else:
            return self.__class__.RowType.LAP


if __name__ == '__main__':
    with urllib.request.urlopen(
            'http://www.tdsystem.co.jp/Record.php?' +
            'Y=2018&M=6&G=154&GL=0&L=1&Page=ProList.php&P=10&S=2&Lap=1&Cls=50'
    ) as res:
        p = RecordPageParser(BeautifulSoup(res, 'lxml'))
        params = p.get_query_params()
        classes = p.get_available_classes()

    for cls in classes.keys():
        params['Cls'] = cls
        req = urllib.request.Request('{}?{}'.format(
            'http://www.tdsystem.co.jp/Record.php',
            urllib.parse.urlencode(params)))
        print(req.get_full_url())
        with urllib.request.urlopen(req) as res:
            p = RecordPageParser(BeautifulSoup(res, 'lxml'))
            rs = p.get_records()
            for r in rs:
                print(r)
