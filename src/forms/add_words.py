from aqt.qt import QDialog, Qt
from .dialog_ui import Ui_Dialog
import os
import json

class AddWordsDialog(QDialog):
    def __init__(self, mw):
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        self.mw = mw
        self.form = Ui_Dialog()
        self.form.setupUi(self)
        self.form.buttonBox.accepted.connect(self.accept)
        self.form.buttonBox.rejected.connect(self.reject)
        
        # Load config
        addon_dir = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(addon_dir, "config.json")) as f:
            self.config = json.load(f)
        
        # Set up word input
        self.form.wordInput.setPlaceholderText("Enter word")
        
        self.resize(400, 100)
        self.setWindowTitle("Add from Cambridge Dictionary")
        
    def accept(self):
        super().accept()
        
    def get_word(self):
        """Get the word from the text input."""
        text = self.form.wordInput.text().strip()
        if not text:
            return ""
        return text
