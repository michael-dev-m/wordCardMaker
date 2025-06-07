import shutil
import json
import os
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, showWarning, askUser
from anki.notes import Note

from .forms.add_words import AddWordsDialog
from .parser.parser import CambridgeDict, LanGeekDict, download_file, OxfordDict


CLOZE = 1
DEFAULT_LATEX_PRE = ('\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n'
                     + '\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n'
                     + '\\begin{document}\n')
DEFAULT_LATEX_POST = '\\end{document}'

AVAILABLE_IMAGE = '_available.jpg'
SEPARATOR_IMG = '&nbsp;'
SEPARATOR_EXAMPLES = '<br>'
PRON_CAMBRIDGE = 'https://dictionary.cambridge.org/pronunciation/english/'


addon_dir = os.path.dirname(__file__)
template_dir = os.path.join(addon_dir, 'templates')


def get_config():
    with open(os.path.join(addon_dir, "config.json")) as f:
        return json.load(f)


def load_file_from_templates_folder(filename):
    with open(os.path.join(template_dir, filename), 'r') as f:
        return f.read()


def get_definition_limit(config: dict):

    try:
        definition_limit = int(config["definition_limit"])
    except ValueError:
        return 1
    except TypeError:
        return 1
    except KeyError:
        return 1
    else:
        return definition_limit if definition_limit > 1 else 1


def get_or_create_deck(config: dict):
    """
    Get or create the Dictionary deck.

    """
    deck_name = config["deck_name"]
    deck_id = mw.col.decks.id(deck_name)
    deck = mw.col.decks.get(deck_id)
    return deck


def available_image_is_media(filename):

    if not os.path.isfile(os.path.join(mw.col.media.dir(), filename)):
        shutil.copy(os.path.join(template_dir, filename),
                    mw.col.media.dir())

def get_or_create_note_model(config: dict):
    """
    Get or create the note model for Dictionary cards.

    """
    model_name = config["model_name"]

    model = mw.col.models.by_name(model_name)
    if model:
        return model

    # Create available image
    available_image_is_media(AVAILABLE_IMAGE)

    # Create new model
    model = mw.col.models.new(model_name)

    # Set model type
    model['type'] = CLOZE
    model['latex_pre'] = DEFAULT_LATEX_PRE
    model['latex_post'] = DEFAULT_LATEX_POST

    # Create fields
    fields = ["Word", "Images", "PartOfSpeech", "Definition",
              "FirstExample", "AudioOfTheFirstExample",
              "SecondExample", "AudioOfTheSecondExample",
              "ThirdExample", "AudioOfTheThirdExample",
              "Translate", "TranscriptionUK", "AudioUK", "TranscriptionUS", "AudioUS",
              "Source", "SourceOfPronunciation"]
    for field in fields:
        field_dict = mw.col.models.new_field(field)
        mw.col.models.add_field(model, field_dict)

    templates = [
        {
            'name': 'Cloze Card with tree examples',
            'qfmt': load_file_from_templates_folder("complete_sentences_front.xml"),
            'afmt': load_file_from_templates_folder("complete_sentences_back.xml")
        }
    ]

    model['tmpls'] = templates
    model['css'] = load_file_from_templates_folder("styles.css")

    # Add the model into collection
    mw.col.models.add(model)

    # Save change
    mw.col.models.flush()
    return model


def handle_duplicate_word(word, deck_id):
    """
    Handle duplicate word by asking user what to do.

    """
    deck = mw.col.decks.get(deck_id)
    if not deck:
        return False, None

    # Escape special characters in word
    escaped_word = word.replace('"', '\\"')

    # Search for notes with the same word
    query = f'word:"{escaped_word}" deck:"{deck["name"]}"'
    note_ids = mw.col.find_notes(query)

    if not note_ids:
        return False, None

    # Ask user what to do
    msg = f'The word "{word}" already exists in deck "{deck["name"]}".\nDo you want to replace it with new data?'
    if askUser(msg, title="Duplicate Word Found"):
        return True, note_ids[0]  # Return True and the note ID to update
    return True, None  # Return True but no note ID means skip


def add_pictures_from_langeek(query: str, cards: list):
    langeek_cards = LanGeekDict(query).cards
    # take pictures from LanGeek
    for card in cards:
        for langeek_card in langeek_cards:
            card.add_images_equal_pos(langeek_card)


def get_oxford_card(query: str, def_limit: int):
    parser = OxfordDict(query, dictionary_type='am-en', definition_limit=def_limit)
    add_pictures_from_langeek(query, parser.cards)
    return parser.cards


def get_cambridge_cards(query: str, def_limit: int):

    # get main meaning from English-Russian Cambridge Dictionary
    parser = CambridgeDict(query, dictionary_type='en-ru', definition_limit=def_limit)
    main_cards = parser.cards

    if main_cards:
        # take pictures from English Cambridge Dictionary
        parser.fetch_cards(query, dictionary_type='en')
        donor_cards = parser.cards

        for main_card in main_cards:
            for donor_card in donor_cards:
                main_card.add_images_equal_pos(donor_card)
    else:
        # get main meaning from English Cambridge Dictionary
        main_cards = CambridgeDict(query, dictionary_type='en', definition_limit=def_limit).cards

    add_pictures_from_langeek(query, main_cards)

    return main_cards


def fill_fields_out(note, card, index=0):

    note.fields[0] = f'{card.word}|{index + 1}|{card.pos}'  # Word

    if card.src_images:
        filenames = []
        for url in card.src_images:
            filename = f"{card.word}_{card.pos}_{''.join(char for char in url if char.isdigit())}.jpeg"
            filenames.append(download_file(url, mw.col.media.dir(), filename))
        note.fields[1] = SEPARATOR_IMG.join([f'<img src="{f}">' for f in filenames])

    note.fields[2] = card.pos  # PartOfSpeech

    block = card.data[index]

    note.fields[3] = block['definition']  # Definitions

    try:
        note.fields[4] = block['examples'][0]  # Example0
        note.fields[5] = ''  # Audio
        note.fields[6] = block['examples'][1]  # Example1
        note.fields[7] = ''  # Audio
        note.fields[8] = block['examples'][2]  # Example2
        note.fields[9] = ''  # Audio
    except KeyError:
        pass
    except IndexError:
        pass

    note.fields[10] = block.setdefault('translate', '')  # Translate

    note.fields[11] = card.pron_uk  # PronUK

    note.fields[12] = f"[sound:{download_file(card.src_uk_mp3, mw.col.media.dir(), f'{card.word}_uk.mp3')}]" if card.src_uk_mp3 else '' # AudioUK

    note.fields[13] = card.pron_us  # PronUS

    note.fields[14] = f"[sound:{download_file(card.src_us_mp3, mw.col.media.dir(), f'{card.word}_us.mp3')}]" if card.src_us_mp3 else ''  # AudioUS

    note.fields[15] = f"<a href='{card.source}'>(Source)</a>" if card.source else ''  # Source

    note.fields[16] = f"<a href='{PRON_CAMBRIDGE}{card.word.split(' ')[0]}'>(CheckPronunciationCambridge)</a>"

    note.tags = [card.pos, card.word[0]]  # Tags


def add_word(word, dictionary_name):
    """
    Add a word to Anki deck.

    """
    try:
        config = get_config()
        deck = get_or_create_deck(config)
        model = get_or_create_note_model(config)
        definition_limit = get_definition_limit(config)

        # # Check for duplicates in the specific deck
        # is_duplicate, note_id = handle_duplicate_word(word, deck['id'])
        # if is_duplicate:
        #     if not note_id:  # User chose to skip
        #         return

        if dictionary_name == 'Oxford':
            cards = get_oxford_card(word, definition_limit)
        else:
            cards = get_cambridge_cards(word, definition_limit)

        if not cards:
            raise Exception("No data found for word")

        for card in cards:
            # make an insert {{c1: word}} for the fields of Definition and Examples
            card.cloze_anki()

            for index in range(len(card.data)):
                #  Create new note
                note = Note(mw.col, model)
                # Map data to note fields
                fill_fields_out(note, card, index)
                # Save new note
                mw.col.add_note(note, deck["id"])

    except Exception as e:
        raise Exception(f"Error adding word {word}: {str(e)}")


def add_from_oxford_dictionary():
    """
        Handle the button click in main window.

    """
    dictionary_name = 'Oxford'
    add_from_dictionary(dictionary_name)


def add_from_cambridge_dictionary():
    """
    Handle the button click in main window.

    """
    dictionary_name = 'Cambridge'
    add_from_dictionary(dictionary_name)


def add_from_dictionary(dictionary_name):
    dialog = AddWordsDialog(mw, dictionary_name)
    if dialog.exec():
        word = dialog.get_word()
        if word:
            try:
                add_word(word, dictionary_name)
                showInfo(f"Successfully added '{word}' from {dictionary_name} Dictionary.")
            except Exception as e:
                showWarning(f"Error adding word: {str(e)}")


# Create a menu action
action = QAction("Add from Cambridge Dictionary", mw)
action.triggered.connect(add_from_cambridge_dictionary)
action.setToolTip("Add word from Cambridge Dictionary")

action_oxford = QAction("Add from Oxford Dictionary", mw)
action_oxford.triggered.connect(add_from_oxford_dictionary)
action_oxford.setToolTip("Add word from Oxford Dictionary")

# Add menu item to Tools menu
mw.form.menuTools.addAction(action)
mw.form.menuTools.addAction(action_oxford)

# Create and add toolbar
toolbar = QToolBar("Add from Dictionary")
toolbar.addAction(action)
toolbar.addAction(action_oxford)
mw.addToolBar(toolbar)

