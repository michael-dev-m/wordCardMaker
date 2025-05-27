import re
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass
import requests
from requests import Session


LIMIT_OF_THE_SAME_WORDS = 3

endings = ['ing', 'ily', 'ly', 'es', 'ed', 's', 'd', 'e', 'y']


@dataclass
class Card:

    word: str
    pos: str
    source: str
    src_uk_mp3: str = None
    pron_uk: str = None
    src_us_mp3: str = None
    pron_us: str = None
    data: list = None   #[{'definition': str, 'examples': [], 'translate': str}, {}]
    src_images: list = None

    def add_images(self, donor):
        self.src_images.extend(donor.src_images)

    def add_images_equal_pos(self, donor):
        if self.word == donor.word and self.pos == donor.pos:
            self.src_images.extend(donor.src_images)

    def _pattern(self, prefix):
        return re.compile(r'\b(' + re.escape(prefix) + r'\w*)', re.IGNORECASE)

    def _replacer_c1(self, match):
        _word = match.group(1)
        return f"{{{{c1::{_word}}}}}"

    def cloze_anki(self):
        """
        This method in the examples field encloses the search word in double curly brackets
        and adds {{c1::word::part of speech}} to the definition field.
        For example: 'I thought he {{c1::handled}} the situation very well.'

        """
        prefix = strip_ending(self.word)
        for i in range(len(self.data)):
            try:
                self.data[i]['definition'] = f"{{{{c1::{self.word}::{self.pos}}}}} - {self.data[i]['definition']}"
            except KeyError:
                self.data[i]['definition'] = f"{{{{c1::{self.word}::{self.pos}}}}} "
            try:
                self.data[i]['examples'] = [self._pattern(prefix).sub(self._replacer_c1, text) for text in
                                            self.data[i]['examples']]
            except KeyError:
                self.data[i]['examples'] = []

    def _replacer(self, match):
        _word = match.group(1)
        return f"{{{_word}}}"

    def put_word_in_curly_brackets(self):
        """
        This method in the examples field encloses the search word in curly brackets.
        For example: 'I thought he {handled} the situation very well.'
        """
        prefix = strip_ending(self.word)
        for i in range(len(self.data)):
            try:
                self.data[i]['examples'] = [self._pattern(prefix).sub(self._replacer, text) for text in
                                            self.data[i]['examples']]
            except KeyError:
                self.data[i]['examples'] = []


def strip_ending(word):
    for ending in endings:
        if word.endswith(ending):
            return word[:-len(ending)]
    return word


def download_file(url: str, filedir: str, filename: str) -> str:
    """
    Download file.

    """
    if not url:
        return ""

    # Create browser-like headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://dictionary.cambridge.org/",
        "Connection": "keep-alive"
    }

    # Create filepath
    filepath = os.path.join(filedir, filename)

    # Check if file already exists
    if os.path.exists(filepath):
        return filename

    # Try downloading with retries
    max_retries = 3
    retry_interval = 2  # seconds

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=45)

            if response.status_code != 200:
                if attempt < max_retries - 1:
                    time.sleep(retry_interval)
                    continue
                return ""

            # Create file
            with open(filepath, "wb") as f:
                f.write(response.content)

            return filename

        except Exception as e:
            # Clean up partial file if it exists
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass

            if attempt < max_retries - 1:
                time.sleep(retry_interval)
                continue
            print(f"Error downloading file {url}: {str(e)}")

    return ""


class OxfordDict:
    """
    Parser from Oxford Learners Dictionary.

    """
    path_dictionary = {'en': '/search/english/',
                  'am-en': '/search/american_english/'}
    base_url = 'https://www.oxfordlearnersdictionaries.com/'

    def __init__(self, word, dictionary_type='en', definition_limit = 1):
        self.def_limit = definition_limit
        self.soup = BeautifulSoup()
        self.cards = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        })
        self.fetch_cards(word, dictionary_type)

    def fetch_cards(self, word, dictionary_type='en'):
        url = self._make_url(word, dictionary_type)
        self.get_soup(url)
        self.make_cards()

    def get_soup(self, url):
        self.response = fetch_with_redirects(session=self.session, url=url)
        self.soup = BeautifulSoup(self.response.text, "html.parser")

    def _make_url(self, word, key):
        url_with_path = urljoin(self.__class__.base_url, self.__class__.path_dictionary[key])
        query = f"?q={word.replace(' ', '+')}"
        return urljoin(url_with_path, query)

    def make_cards(self):
        self._make_card()
        self._find_the_same_words()
        for url in self._additional_pos_urls:
            self.get_soup(url)
            self._make_card()

    def _find_the_same_words(self):
        block_matches = self.soup.find('ul', attrs={'class': 'list-col'})

        items = block_matches.find_all('a')
        self._additional_pos_urls = set()
        for item in items:
            if item.find('span', class_='arl1'):
                self._additional_pos_urls.add(item.get('href'))

    def _make_card(self):
        main_container = self.soup.find('div', {'class': 'main-container'})
        header = main_container.find('div', { 'class': 'top-container'})

        word = header.find(re.compile('^h')).get_text()
        pos = header.find('span', class_='pos').get_text()
        card = Card(word, pos, self.response.url)

        try:
            blok_uk = header.find('div', title=re.compile(" English"))

            card.src_uk_mp3 = blok_uk.get('data-src-mp3')
            card.pron_uk = blok_uk.parent.find('span', class_='phon').get_text(strip=True)
        except AttributeError:
            pass

        try:
            blok_us = main_container.find('div', title=re.compile(" American"))
            
            card.src_us_mp3 = blok_us.get('data-src-mp3')
            card.pron_us = blok_us.parent.get_text(strip=True)
        except AttributeError:
            pass

        def has_li_and_id(tag):
            return tag.name == 'li' and tag.has_attr('id')

        blocks = main_container.find_all(has_li_and_id, limit=self.def_limit)
        card.data = []
        for block in blocks:
            data = dict()
            try:
                data['definition'] = block.find('span', class_='def').get_text()
            except AttributeError:
                data['definition'] = block.find('span', class_='xrefs').get_text()

            try:
                data['examples'] = [x.get_text() for x in block.find_all('span', class_='x')]
            except AttributeError:
                data['examples'] = []

            data['translate'] = ''
            card.data.append(data)

        try:
            src_img = self.soup.find('img', class_='thumb').get('src')
            card.src_images = [src_img.replace('thumb', 'fullsize')]
        except AttributeError:
            pass

        self.cards.append(card)


class CambridgeDict:
    """
    Parser from Cambridge Dictionary.

    """
    dictionary = {'en': '/dictionary/english/',
                  'en-ru': '/dictionary/english-russian/',}
    url_parse = urlparse('https://dictionary.cambridge.org/')

    def __init__(self, word, dictionary_type='en-ru', definition_limit=1):
        self.def_limit = definition_limit
        self.cards = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        })
        self.fetch_cards(word, dictionary_type)

    def fetch_cards(self, word, dictionary_type='en'):
        self.response = fetch_with_redirects(session=self.session,
                                             url=self._make_url(word, dictionary_type)
                                             )
        self.soup = BeautifulSoup(self.response.text, "html.parser")
        self.make_cards()

    def _make_url(self, word, dictionary_type):

        url_with_path = urljoin(self.__class__.url_parse.geturl(),
                                self.__class__.dictionary[dictionary_type]
                                )
        return urljoin(url_with_path, word.replace(' ', '-'))

    def make_cards(self):
        # there are some dictionaries on a page of english dictionary
        # so we take only first
        first_dictionary = self.soup.find('div', {'class': 'pr dictionary'})
        if first_dictionary:
            # for a page of english dictionary
            body_elements = first_dictionary.find_all('div', {'class': "pr entry-body__el"},
                                               limit=LIMIT_OF_THE_SAME_WORDS)
        else:
            # for a page of english-russian dictionary
            body_elements = self.soup.find_all('div', { 'class': "pr entry-body__el"},
                                           limit=LIMIT_OF_THE_SAME_WORDS)

        self.cards = []

        if body_elements:
            # for general page
            for body_element in body_elements:
                self._make_card(body_element)
        else:
            # for a page with a phase verb
            body_element = self.soup.find('div', {'class': "pv-block"},)
            if body_element:
                self._make_card(body_element)

    def _make_card(self, element):
        """
        It creates a card from the element of the body.
        :param element: the element containing the coup with the header (word, part of speech, pronunciation)
        :return: it saves the card to the instance of class CambridgeDict
        """

        word = element.find('div', class_='di-title').get_text()
        try:
            pos = element.find('span', class_='pos dpos').get_text()
        except AttributeError:
            pos = element.find('div', class_='def ddef_d db').get_text()

        card = Card(word, pos, self.response.url)

        try:
            blok_uk = element.find('span', string='uk').parent
            src_uk = blok_uk.find('source', type='audio/mpeg').get('src')
            card.src_uk_mp3 = CambridgeDict.url_parse._replace(path=src_uk).geturl()
            card.pron_uk = blok_uk.find('span', class_='pron dpron').get_text(strip=True)
        except AttributeError:
            pass

        try:
            blok_us = element.find('span', string='us').parent
            src_us = blok_us.find('source', type='audio/mpeg').get('src')
            card.src_us_mp3 = CambridgeDict.url_parse._replace(path=src_us).geturl()
            card.pron_us = blok_us.find('span', class_='pron dpron').get_text(strip=True)
        except AttributeError:
            pass
        # if there is no American transcription, let's take British
        if not card.pron_us and card.pron_uk:
            card.pron_us = card.pron_uk

        # block contains the definition and the examples
        blocks = element.find_all('div', class_='def-block ddef_block', limit=self.def_limit)
        card.data = []
        for block in blocks:
            data = dict()
            data['definition'] = block.find('div', {'class': 'def ddef_d db'}).get_text()

            try:
                examps = block.find_all('div', class_='examp dexamp')
                data['examples'] = [examp.get_text() for examp in examps]
            except AttributeError:
                data['examples'] = []

            try:
                data['translate'] = block.find('span', {'lang': 'ru'}).get_text()
            except AttributeError:
                data['translate'] = ''

            card.data.append(data)

        try:
            card.src_images = []
            parts = element.find_all('amp-img', class_='dimg_i hp')
            for part in parts:
                src = part.get('src')
                src_img = src.replace('thumb', 'full')
                card.src_images.append( CambridgeDict.url_parse._replace(path=src_img).geturl())
        except AttributeError:
            pass

        self.cards.append(card)


def fetch_with_redirects(session: Session, url: str, max_redirects: int = 10) -> requests.Response:
    """
    Fetch URL with manual redirect handling.

    """
    current_url = url

    for _ in range(max_redirects):
        response = session.get(current_url, allow_redirects=False)

        if response.status_code == 200:
            return response
        elif response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get('Location')
            if not location:
                raise Exception("Redirect without Location header")

            if not urlparse(location).netloc:
                current_url = urljoin(url, location)
            else:
                current_url = location
            continue
        else:
            response.raise_for_status()

    raise Exception("Too many redirects")


class LanGeekDict:

    api_url = "https://api.langeek.co/v1/cs/en/word/"
    base_url = "https://dictionary.langeek.co/en/word/"

    def __init__(self, word: str):

        self.cards = []
        self.response_json = self.fetch_point(word)
        self.make_cards()

    def make_cards(self):
        """
        Create cards only with pictures
        :return: list of cards
        """
        for item in self.response_json:
            for pos in item["translations"].keys():
                for meaning in item["translations"][pos]:
                    try:
                        url = urljoin(self.__class__.base_url,
                                      f'{item["id"]}?entry={item["entry"]}')
                        self.cards.append(Card(word=item["entry"],
                                               pos=pos,
                                               source= url,
                                               data=[{'definition': meaning["translation"]}],
                                               src_images=[meaning["wordPhoto"]["photo"]]
                                               )
                                          )
                    except KeyError:
                        pass
                    except TypeError:
                        pass

    def fetch_point(self, word):
        response = requests.get(self.__class__.api_url,
                                params={"term": word,
                                        "filter": ",inCategory,photo"},
                                stream=True,
                                timeout=5,
                                allow_redirects=False,
                                )
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
