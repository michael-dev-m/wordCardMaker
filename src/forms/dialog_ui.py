from aqt.qt import (
    QVBoxLayout, QLineEdit,
    QDialogButtonBox, Qt, QLabel
)

class Ui_Dialog:
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        
        # Create main layout
        self.verticalLayout = QVBoxLayout(Dialog)
        
        # Add label
        self.label = QLabel(Dialog)
        self.label.setText("Enter word:")
        self.verticalLayout.addWidget(self.label)
        
        # Add word input
        self.wordInput = QLineEdit(Dialog)
        self.wordInput.setPlaceholderText("Enter word to add")
        self.verticalLayout.addWidget(self.wordInput)
        
        # Add button box
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.verticalLayout.addWidget(self.buttonBox)
