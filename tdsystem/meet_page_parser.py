import re
import urllib.request
from enum import Enum
from typing import Dict, List

from bs4 import BeautifulSoup
from bs4.element import Tag

from parser_base import Parser


class Sex(Enum):
    M = '男子'
    F = '女子'
    X = '混合'


class Style(Enum):
    FR = '自由形'
    BR = '平泳ぎ'
    BA = '背泳ぎ'
    FLY = 'バタフライ'
    IM = '個人メドレー'
    FRR = 'フリーリレー'
    MR = 'メドレーリレー'


class Race:
    def __init__(self,
                 sex: Sex = None,
                 distance: int = 0,
                 style: Style = None,
                 q_params: Dict[str, str] = None):
        self.sex = sex
        self.distance = distance
        self.style = style
        self.q_params = q_params

    def __str__(self):
        return 'sex={}, distance={}, style={}, q_params={}'.format(
            self.sex, self.distance, self.style, self.q_params)

    def add_q_param(self, key: str, val: str):
        if not self.q_params:
            self.q_params = {}
        self.q_params[key] = val


class MeetPageParser(Parser):
    def __init__(self, page: Tag):
        self.page = page

    def __get_race_query_params(self, form) -> Dict[str, str]:
        params = {}
        params['action'] = form.get('action')
        for input in form.find_all('input', attrs={'type': 'hidden'}):
            params[input.get('name')] = input.get('value')
        return params

    SEX_PAT = re.compile(r'女子|男子|混合')
    INDV_DIST_PAT = re.compile(r'([0-9]+)m')
    RELAY_DIST_PAT = re.compile(r'4×([0-9]+)m')
    STYLE_PAT = re.compile(r'自由形|背泳ぎ|平泳ぎ|バタフライ|個人メドレー|フリーリレー|メドレーリレー')

    def get_races(self) -> List[Race]:
        rs = []
        form = self.page.find('form', attrs={'name': 'gamelist'})
        params = self.__get_race_query_params(form)
        for tr in form.find_all('tr'):
            r = Race(q_params=params.copy())
            for td in tr.find_all('td'):
                txt = self.normalize(td.get_text())
                if not txt:
                    continue
                m = self.__class__.SEX_PAT.match(txt)
                if m:
                    r.sex = Sex(m.group(0))
                    continue
                m = self.__class__.INDV_DIST_PAT.match(txt)
                if m:
                    r.distance = int(m.group(1))
                m = self.__class__.RELAY_DIST_PAT.match(txt)
                if m:
                    r.distance = int(m.group(1)) * 4
                m = self.__class__.STYLE_PAT.match(txt)
                if m:
                    r.style = Style(m.group(0))
            button = tr.find('button')
            if button:
                r.add_q_param(button.get('name'), button.get('value'))
            rs.append(r)
        return rs


if __name__ == '__main__':
    with urllib.request.urlopen(
            'http://www.tdsystem.co.jp/ProList.php?Y=2018&M=6&GL=0&G=154'
    ) as res:
        p = MeetPageParser(BeautifulSoup(res, 'lxml'))
        rs = p.get_races()
        for r in rs:
            print(r)
