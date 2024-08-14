import sys
from PyQt5 import QtWidgets
from src import db_func


class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Login")
        self.setGeometry(400, 200, 300, 150)

        # Create widgets
        self.username_label = QtWidgets.QLabel("Username:", self)
        self.username_input = QtWidgets.QLineEdit(self)

        self.password_label = QtWidgets.QLabel("Password:", self)
        self.password_input = QtWidgets.QLineEdit(self)
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        self.login_button = QtWidgets.QPushButton("Login", self)
        self.register_button = QtWidgets.QPushButton("Register", self)

        # Set layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addWidget(self.register_button)
        self.setLayout(layout)

        # Connect buttons to functions
        self.login_button.clicked.connect(self.login)
        self.register_button.clicked.connect(self.register)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if db_func.verify_password(username, password):
            QtWidgets.QMessageBox.information(self, "Success", "Login successful!")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid username or password.")

    def register(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if username and password:
            if db_func.get_user(username):
                QtWidgets.QMessageBox.warning(self, "Error", "Username already exists.")
            else:
                db_func.store_user(username, password)
                QtWidgets.QMessageBox.information(self, "Success", "User registered successfully.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter both username and password.")

if __name__ == "__main__":
    db_func.init_db()  # Initialize the database
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
