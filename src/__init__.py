import shutil
import json
import os
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, showWarning, askUser
from anki.notes import Note

from .forms.add_words import AddWordsDialog
from .parser.parser import CambridgeDict, LanGeekDict, download_file


CLOZE = 1
DEFAULT_LATEX_PRE = ('\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n'
                     + '\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n'
                     + '\\begin{document}\n')
DEFAULT_LATEX_POST = '\\end{document}'

AVAILABLE_IMAGE = '_available.jpg'
SEPARATOR_IMG = '&nbsp;'
SEPARATOR_EXAMPLES = '<br>'


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
    fields = ["Word", "Images", "PartOfSpeech", "Definition", "Examples", "Audio",
              "Translate", "PronUK", "AudioUK", "PronUS", "AudioUS", "Source"]
    for field in fields:
        field_dict = mw.col.models.new_field(field)
        mw.col.models.add_field(model, field_dict)

    templates = [
        {
            'name': 'Cloze Card',
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

    langeek_cards = LanGeekDict(query).cards
    # take pictures from LanGeek
    for main_card in main_cards:
        for langeek_card in langeek_cards:
            main_card.add_images_equal_pos(langeek_card)

    return main_cards


def fill_fields_out(note, card, index=0):

    note.fields[0] = f'{card.word}|{index + 1}|{card.pos}'  # Word

    if not card.src_images:
        note.fields[1] = f'<img src="{AVAILABLE_IMAGE}">'
    else:
        filenames = []
        for url in card.src_images:
            filename = f"{card.word}_{card.pos}_{''.join(char for char in url if char.isdigit())}.jpeg"
            filenames.append(download_file(url, mw.col.media.dir(), filename))
        note.fields[1] = SEPARATOR_IMG.join([f'<img src="{f}">' for f in filenames])

    note.fields[2] = card.pos  # PartOfSpeech

    block = card.data[index]

    note.fields[3] = block['definition']  # Definitions

    def get_unordered_list(lst):
        return f"<ul><li>{'</li><li>'.join(lst)}</li></ul>" if len(lst) > 0 else ''

    note.fields[4] = get_unordered_list(block['examples'])  # Examples

    note.fields[5] = ' '  # Audio

    note.fields[6] = block['translate']  # Translate

    note.fields[7] = card.pron_uk  # PronUK

    note.fields[8] = f"[sound:{download_file(card.src_uk_mp3, mw.col.media.dir(), f'{card.word}_uk.mp3')}]"  # AudioUK

    note.fields[9] = card.pron_us  # PronUS

    note.fields[10] = f"[sound:{download_file(card.src_us_mp3, mw.col.media.dir(), f'{card.word}_us.mp3')}]"  # AudioUS

    note.fields[11] = card.source  # Source

    note.tags = [card.pos, card.word[0]]  # Tags


def add_word(word):
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


def add_from_dictionary():
    """
    Handle the button click in main window.

    """
    dialog = AddWordsDialog(mw)
    if dialog.exec():
        word = dialog.get_word()
        if word:
            try:
                add_word(word)
                showInfo(f"Successfully added '{word}'")
            except Exception as e:
                showWarning(f"Error adding word: {str(e)}")


# Create a menu action
action = QAction("Add from Cambridge Dictionary", mw)
action.triggered.connect(add_from_dictionary)
action.setToolTip("Add word from Cambridge Dictionary")

# Add menu item to Tools menu
mw.form.menuTools.addAction(action)

# Create and add toolbar
toolbar = QToolBar("Cambridge Dictionary")
toolbar.addAction(action)
mw.addToolBar(toolbar)

