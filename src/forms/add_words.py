from aqt.qt import QDialog, Qt
from .dialog_ui import Ui_Dialog
import os
import json

class AddWordsDialog(QDialog):
    def __init__(self, mw, dictionary_name='Cambridge'):
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        self.form = Ui_Dialog()
        self.form.setupUi(self)
        self.form.buttonBox.accepted.connect(self.accept)
        self.form.buttonBox.rejected.connect(self.reject)

        # Set up word input
        self.form.wordInput.setPlaceholderText("Enter word")
        
        self.resize(400, 100)
        self.setWindowTitle(f"Add from {dictionary_name} Dictionary")
        
    def accept(self):
        super().accept()
        
    def get_word(self):
        """Get the word from the text input."""
        text = self.form.wordInput.text().strip()
        if not text:
            return ""
        return text
