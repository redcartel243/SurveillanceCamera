import sys
from PyQt5 import QtWidgets, QtCore
from src.db_func import verify_password, store_user, get_user, init_db


class LoginWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

        self.register_button = None
        self.login_button = None
        self.password_input = None
        self.username_input = None
        self.username_label = None
        self.password_label = None
        self.user_id = None  # To store the logged-in user's ID
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

        if verify_password(username, password):
            QtWidgets.QMessageBox.information(self, "Success", "Login successful!")
            self.user_id = get_user(username)[0]  # Get the user ID from the database
            self.accept()  # Close the dialog and indicate success
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid username or password.")

    def register(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if username and password:
            if get_user(username):
                QtWidgets.QMessageBox.warning(self, "Error", "Username already exists.")
            else:
                store_user(username, password)
                QtWidgets.QMessageBox.information(self, "Success", "User registered successfully.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter both username and password.")

    def get_user_id(self):
        return self.user_id


if __name__ == "__main__":
    init_db()  # Initialize the database
    app = QtWidgets.QApplication(sys.argv)
    login_window = LoginWindow()

    if login_window.exec_() == QtWidgets.QDialog.Accepted:
        print(f"User ID: {login_window.get_user_id()} logged in successfully!")
        # You can proceed to launch your main application here

    sys.exit(app.exec_())
