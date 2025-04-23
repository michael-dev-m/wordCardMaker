from selenium.webdriver import FirefoxOptions
from selenium import webdriver
from parser import CambridgeDict, OxfordDict


def create_driver(headless=True):

    firefox_profile_path = '/home/michael/snap/firefox/common/.mozilla/firefox/j4fnjhmr.driver'

    firefox_options = FirefoxOptions()
    if headless:
        firefox_options.add_argument('--headless')
    firefox_options.add_argument('-profile')
    firefox_options.add_argument(firefox_profile_path)
    return webdriver.Firefox(options=firefox_options)


def destroy_driver(driver):
    driver.close()


driver = create_driver(headless=False)

try:
    word = 'life'
    card = CambridgeDict(word, driver)
except Exception:
    raise Exception
finally:
    destroy_driver(driver)
print(card)
