import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QMessageBox

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Context Menu Example")
        self.setGeometry(100, 100, 600, 400)

    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)

        newAction = QAction('New', self)
        openAction = QAction('Open', self)
        quitAction = QAction('Quit', self)

        contextMenu.addAction(newAction)
        contextMenu.addAction(openAction)
        contextMenu.addSeparator()
        contextMenu.addAction(quitAction)

        action = contextMenu.exec_(self.mapToGlobal(event.pos()))

        if action == newAction:
            self.show_message("New was clicked")
        elif action == openAction:
            self.show_message("Open was clicked")
        elif action == quitAction:
            self.close()

    def show_message(self, message):
        QMessageBox.information(self, "Message", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
