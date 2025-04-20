import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dataclasses import dataclass
import urllib.request


user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0'


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

    def get_html(self, url: str):

        # user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0'
        # values = {'accept': 'image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5',
        #           'accept-encoding': 'gzip, deflate, br, zstd',
        #           'accept-language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'}
        # headers = {'User-Agent': user_agent}
        #
        # data = urllib.parse.urlencode(values)
        # data = data.encode('ascii')
        # req = urllib.request.Request(url, data, headers)
        #
        # with urllib.request.urlopen(req) as response:
        #     the_page = response.read()
        # return the_page
        pass



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
    url = 'https://www.oxfordlearnersdictionaries.com/definition/english/'

    def __init__(self, word):

        url = urllib.parse.urljoin(CambridgeDict.url_parse.geturl(), word)

        markup = self.get_html(url)

        self.soup = BeautifulSoup(markup, "html.parser")

        webtop = self.soup.find('div', { 'class': 'webtop-g'})

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

    def __init__(self, word):

        url = urllib.parse.urljoin(CambridgeDict.url_parse.geturl(), word)

        markup = self.get_html(url)

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


if __name__ == '__main__':
    pass