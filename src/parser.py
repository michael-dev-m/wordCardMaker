import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dataclasses import dataclass
import urllib.request


@dataclass
class CardGrabber:

    soup: BeautifulSoup
    word: str
    pos: str
    src_uk_mp3: str = None
    pron_uk: str = None
    src_us_mp3: str = None
    pron_us: str = None
    definitions: list = None
    ru: str = None
    src_images: list = None

    def __str__(self):
        return (f"word: {self.word}"
                f"\n part of speech: [{self.pos}]"
                f"\n src-mp3 (UK): {self.src_uk_mp3}"
                f"\n pron (UK): {self.pron_uk}"
                f"\n src-mp3 (US): {self.src_us_mp3}"
                f"\n pron (US): {self.pron_us}"
                f"\n definitions: {self.definitions}"
                f"\n ru: {self.ru}"
                f"\n src_images: {self.src_images}")


class OxfordDict(CardGrabber):
    """
    Grabber from Oxford Learners Dictionary.

    """
    url_parse = urlparse('https://www.oxfordlearnersdictionaries.com/definition/american_english/')

    def __init__(self, word, driver):

        url = urllib.parse.urljoin(OxfordDict.url_parse.geturl(), word)

        driver.get(url)
        markup = driver.page_source

        self.soup = BeautifulSoup(markup, "html.parser")

        webtop = self.soup.find('div', { 'class': 'top-container'})

        self.word = webtop.find('h2', class_='h').get_text()
        self.pos = webtop.find('span', class_='pos').get_text()

        try:
            blok_uk = self.soup.find('div', title=re.compile("pronunciation English"))
            self.src_uk_mp3 = blok_uk.get('data-src-mp3')
            self.pron_uk = blok_uk.parent.get_text(strip=True)
        except AttributeError:
            pass

        try:
            blok_us = self.soup.find('div', title=re.compile("pronunciation American"))
            self.src_us_mp3 = blok_us.get('data-src-mp3')
            self.pron_us = blok_us.parent.get_text(strip=True)
        except AttributeError:
            pass

        main_definitions = self.soup.find('span', class_='sn-gs')
        self.definitions = [x.get_text() for x in main_definitions.find_all('span', class_='def')]

        try:
            src_img = self.soup.find('img', class_='thumb').get('src')
            self.src_images = [src_img.replace('thumb', 'fullsize')]
        except AttributeError:
            pass


class CambridgeDict(CardGrabber):
    """
    Grabber from Cambridge Dictionary.

    """

    url_parse = urlparse('https://dictionary.cambridge.org/dictionary/english/')

    def __init__(self, word, driver):

        url = urllib.parse.urljoin(CambridgeDict.url_parse.geturl(), word)

        driver.get(url)
        markup = driver.page_source

        self.soup = BeautifulSoup(markup, "html.parser")

        pos_header = self.soup.find('div', class_='pos-header dpos-h')
        self.word = pos_header.find('div', class_='di-title').get_text()
        self.pos = pos_header.find('span', class_='pos dpos').get_text()

        try:
            blok_uk = pos_header.find('span', string='uk').parent
            src_uk_mp3 = blok_uk.find('source', type='audio/mpeg').get('src')
            self.src_uk_mp3 = CambridgeDict.url_parse._replace(path=src_uk_mp3).geturl()
            self.pron_uk = blok_uk.find('span', class_='pron dpron').get_text(strip=True)
        except AttributeError:
            pass

        try:
            blok_us = pos_header.find('span', string='us').parent
            src_us_mp3 = blok_us.find('source', type='audio/mpeg').get('src')
            self.src_us_mp3 = CambridgeDict.url_parse._replace(path=src_us_mp3).geturl()
            self.pron_us = blok_us.find('span', class_='pron dpron').get_text(strip=True)
        except AttributeError:
            pass

        body = self.soup.find('div', class_='sense-body dsense_b')
        self.definitions = [body.find('div', {'class': 'def ddef_d db'}).get_text()]
        try:
            self.src_images = []
            parts = body.find_all('amp-img', class_='dimg_i hp')
            for part in parts:
                src = part.get('src')
                src_img = src.replace('thumb', 'full')
                self.src_images.append( CambridgeDict.url_parse._replace(path=src_img).geturl())
        except AttributeError:
            pass
        try:
            self.ru = body.find('span', {'lang': 'ru'}).get_text()
        except AttributeError:
            pass
