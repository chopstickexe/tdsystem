import pickle
import time
import urllib.request
from logging import INFO, Formatter, StreamHandler, getLogger
from typing import Dict, List

from bs4 import BeautifulSoup

from meet_page_parser import MeetPageParser, Race
from month_page_parser import Meet, MonthPageParser
from record_page_parser import Record, RecordPageParser

logger = getLogger(__name__)
handler = StreamHandler()
handler.setFormatter(Formatter('%(asctime)s %(levelname)s: %(message)s'))
handler.setLevel(INFO)
logger.setLevel(INFO)
logger.addHandler(handler)


class Crawler:
    prev = None
    INTERVAL_SEC = 5

    @staticmethod
    def __fetch(url):
        if Crawler.prev:
            past = time.time() - Crawler.prev
            wait = 0 if past > Crawler.INTERVAL_SEC else Crawler.INTERVAL_SEC
            time.sleep(wait)
        Crawler.prev = time.time()
        if type(url) is str:
            logger.info(url)
        else:
            logger.info(url.get_full_url())
        return urllib.request.urlopen(url)

    @staticmethod
    def fetch_years(url: str) -> List[str]:
        with Crawler.__fetch(url) as res:
            p = MonthPageParser(BeautifulSoup(res, 'lxml'))
            years = p.get_available_years()
            return years

    @staticmethod
    def fetch_meets(baseurl: str, year: str, month: str) -> List[Meet]:
        req = urllib.request.Request('{}?{}'.format(
            baseurl, urllib.parse.urlencode({
                'Y': year,
                'M': month
            })))
        with Crawler.__fetch(req) as res:
            p = MonthPageParser(
                page=BeautifulSoup(res, 'lxml'),
                year=int(year),
                month=int(month))
            return p.get_meets()

    @staticmethod
    def fetch_races(baseurl: str, q_params: Dict[str, str]) -> List[Race]:
        req = urllib.request.Request('{}?{}'.format(
            baseurl + q_params.pop('action'),
            urllib.parse.urlencode(q_params)))
        with Crawler.__fetch(req) as res:
            p = MeetPageParser(BeautifulSoup(res, 'lxml'))
            return p.get_races()

    @staticmethod
    def fetch_records(baseurl: str, q_params: Dict[str, str]) -> List[Record]:
        url = baseurl + q_params.pop('action')
        req = urllib.request.Request('{}?{}'.format(
            url, urllib.parse.urlencode(q_params)))
        with Crawler.__fetch(req) as res:
            p = RecordPageParser(BeautifulSoup(res, 'lxml'))
            params = p.get_query_params()
            classes = p.get_available_classes()
        if not params:
            params = q_params
        if not classes:
            classes = {'999': 'DUMMY'}  # Put the wildcard class

        rs = []
        for cls in classes.keys():
            params['Cls'] = cls
            req = urllib.request.Request('{}?{}'.format(
                url, urllib.parse.urlencode(params)))
            with urllib.request.urlopen(req) as res:
                p = RecordPageParser(
                    BeautifulSoup(res, 'lxml'), params, classes[cls])
                rs.extend(p.get_records())
        return rs


def crawl_all(base_url: str):
    years = Crawler.fetch_years(baseurl)
    for y in years:
        for m in range(1, 12):
            meets = Crawler.fetch_meets(baseurl, y, m)
            for meet in meets:
                for r in Crawler.fetch_races(baseurl, meet.q_params):
                    Crawler.fetch_records(baseurl, r.q_params)
                    # TODO Store somewhere


def crawl_records(base_url: str,
                  record_page_params: Dict[str, str]) -> List[Record]:
    return Crawler.fetch_records(baseurl, record_page_params)


if __name__ == '__main__':
    baseurl = 'http://www.tdsystem.co.jp/'
    rs = crawl_records(
        baseurl, {
            'action': 'Record.php',
            'Y': '2018',
            'M': '6',
            'GL': '0',
            'G': '154',
            'S': '2',
            'Lap': '1',
            'Cls': '999',
            'L': '1',
            'P': '10'
        })
    with open('records.pickle', 'wb') as f:
        pickle.dump(rs, f, pickle.HIGHEST_PROTOCOL)

    with open('records.pickle', 'rb') as f:
        rs = pickle.load(f)
        for r in rs:
            print(r)
