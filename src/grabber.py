from bs4 import BeautifulSoup


class OxfordDict:
    """
    Grabber from Oxford Learners Dictionary.

    """
    url = 'https://www.oxfordlearnersdictionaries.com/definition/american_english/'

    def __init__(self, markup):

        self.soup = BeautifulSoup(markup, "html.parser")

        webtop = self.soup.find('div', { 'class': 'webtop-g'})

        self.word = webtop.find('h2', class_='h').get_text()
        self.pos = webtop.find('span', class_='pos').get_text()

        pron = self.soup.find('div', class_='pron-gs ei-g')
        sound = pron.find('div', class_='sound audio_play_button pron-usonly icon-audio')
        self.src_mp3 = sound.get('data-src-mp3')
        self.pron = pron.get_text(strip=True)

        main_definitions = self.soup.find('span', class_='sn-gs')
        self.definition = [x.get_text() for x in main_definitions.find_all('span', class_='def')]

        try:
            self.src_img = self.soup.find('img', class_='thumb').get('src')
            self.src_img = self.src_img.replace('thumb', 'fullsize')
        except AttributeError:
            self.src_img = None


    def __str__(self):
        return (f"word: {self.word}"
                f"\n part of speetch: [{self.pos}]"
                f"\n src-mp3: {self.src_mp3}"
                f"\n pron: {self.pron}"
                f"\n definition: {self.definition}"
                f"\n src-img: {self.src_img}")

        # print(self.soup.prettify())


if __name__ == '__main__':
    pass
