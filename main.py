from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QDialog, QCheckBox, QMessageBox, QApplication, QMainWindow, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QListWidget, QListWidgetItem, QWidget, QHBoxLayout, QGraphicsDropShadowEffect, QTextEdit
from PySide6.QtCore import Qt, QPoint, Signal, QThread, Slot, QTimer
from PySide6.QtGui import QMouseEvent, QFont
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException, InvalidSelectorException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from pygame import mixer
from selenium import webdriver
import multiprocessing
import sys
import json
import time
import datetime
import random
import requests
import telebot
from queue import Queue
from threading import Thread
import os
import signal
import zipfile
from threading import Lock

from main_window import Ui_MainWindow

import psutil

current_user_id = None

def get_user_id():
    return current_user_id

class ClickableLabel(QLabel):
    clicked = QtCore.Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
        
class ClickableFrame(QFrame):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = ClickableLabel(self)
        self.label.clicked.connect(self.clicked.emit)
        
class AccountSettingsDialog(QDialog):
    def __init__(self, account_id, account_name, cookies, twitch_cookies, messages, parent=None):
        super(AccountSettingsDialog, self).__init__(parent)
        self.account_id = account_id
        self.account_name = account_name
        self.cookies = cookies
        self.twitch_cookies = twitch_cookies
        self.messages = messages
        self.init_ui()
        self.setGeometry(100, 100, 800, 600)
        self.center_on_screen()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("""
            QDialog {
                background-color: #333;
                color: white;
            }
            QLabel {
                margin-left: 20px;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                margin-top: 5px;
                margin-bottom: 5px;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #555;
                color: white;
                border: 1px solid #666;
                padding: 5px;
                margin: 5px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)

        self.account_name_edit = QLineEdit(self)
        self.account_name_edit.setText(self.account_name)
        self.account_name_edit.setPlaceholderText("Enter account name (up to 30 chars)")
        self.account_name_edit.setMaxLength(30)
        font = QFont()
        font.setFamilies([u"Gotham Pro Black"])
        font.setPointSize(15)
        self.account_name_edit.setFont(font)
        layout.addWidget(self.account_name_edit)

        # Куки
        self.cookies_edit = QTextEdit()
        try:
            cookies_json = json.loads(self.cookies)
            self.cookies_edit.setPlainText(json.dumps(cookies_json, indent=4))
        except json.JSONDecodeError:
            self.cookies_edit.setPlainText("Неверно заданы cookies.")
        self.cookies_edit.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.cookies_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        layout.addWidget(self.cookies_edit)

        # Сообщения
        self.messages_edit = QTextEdit()
        self.messages_edit.setPlainText("\n".join(self.messages.splitlines()))
        self.messages_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        layout.addWidget(self.messages_edit)
        
        # Twitch cookies
        self.twitch_cookies_edit = QTextEdit()
        try:
            twitch_cookies_json = json.loads(self.twitch_cookies)
            self.twitch_cookies_edit.setPlainText(json.dumps(twitch_cookies_json, indent=4))
        except json.JSONDecodeError:
            self.twitch_cookies_edit.setPlainText("Неверно заданы twitch cookies.")
        self.twitch_cookies_edit.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.twitch_cookies_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        layout.addWidget(self.twitch_cookies_edit)

        # Кнопки
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        font = QFont()
        font.setFamilies([u"Gotham Pro Black"])
        font.setPointSize(12)
        save_button.setFont(font)
        cancel_button.setFont(font)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)

        save_button.clicked.connect(self.save_changes)
        cancel_button.clicked.connect(self.reject)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def save_changes(self):
        user_id = get_user_id()
        if user_id is None:
            QMessageBox.critical(self, "Error", "User ID is not set. Please login again.")
            return

        data = {
            'account_id': self.account_id,
            'name': self.account_name_edit.text(),
            'cookies': self.cookies_edit.toPlainText(),
            'twitch_cookies': self.twitch_cookies_edit.toPlainText(),
            'messages': self.messages_edit.toPlainText()
        }
        response = requests.post('http://77.232.131.189:5000/update_kick_account', json=data)
        if response.status_code == 200:
            QMessageBox.information(self, "Success", "Account successfully updated.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to update account. Server responded with an error.")
    
    def center_on_screen(self):
        screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
        
class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super(AddAccountDialog, self).__init__(parent)
        self.setWindowTitle("Add New Account")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(800, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("""
            QDialog {
                background-color: #333;
                color: white;
            }
            QLabel {
                margin-left: 20px;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                margin-top: 5px;
                margin-bottom: 5px;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #555;
                color: white;
                border: 1px solid #666;
                padding: 5px;
                margin: 5px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #777;
            }
            QCheckBox {
                margin-left: 10px;
            }
        """)

        # Название аккаунта
        self.account_name_edit = QLineEdit(self)
        self.account_name_edit.setPlaceholderText("Enter account name (up to 30 chars)")
        self.account_name_edit.setMaxLength(30)
        font = QFont()
        font.setFamilies([u"Gotham Pro Black"])
        font.setPointSize(15)
        self.account_name_edit.setFont(font)
        layout.addWidget(self.account_name_edit)

        # Куки
        self.cookies_edit = QTextEdit(self)
        self.cookies_edit.setPlaceholderText("Вставьте сюда куки...")
        layout.addWidget(self.cookies_edit)

        # Сообщения
        self.messages_edit = QTextEdit(self)
        self.messages_edit.setPlaceholderText("Вставьте сюда сообщения...")
        layout.addWidget(self.messages_edit)

        # Переключатель для Twitch cookies
        self.use_twitch_cookies_checkbox = QCheckBox("Использовать Twitch cookies", self)
        self.use_twitch_cookies_checkbox.stateChanged.connect(self.toggle_twitch_cookies)
        layout.addWidget(self.use_twitch_cookies_checkbox)

        # Twitch cookies
        self.twitch_cookies_edit = QTextEdit(self)
        self.twitch_cookies_edit.setPlaceholderText("Вставьте сюда twitch cookies...")
        self.twitch_cookies_edit.setFixedHeight(100)
        layout.addWidget(self.twitch_cookies_edit)

        # Кнопки
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить", self)
        self.cancel_button = QPushButton("Отменить", self)
        font = QFont()
        font.setFamilies([u"Gotham Pro Black"])
        font.setPointSize(12)
        self.save_button.setFont(font)
        self.cancel_button.setFont(font)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)

        self.save_button.clicked.connect(self.save_account)
        self.cancel_button.clicked.connect(self.reject)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        # Скрытие поля twitch_cookies_edit по умолчанию
        self.twitch_cookies_edit.hide()

    def toggle_twitch_cookies(self, state):
        print(f"Twitch cookies checkbox state changed: {state}")  # Отладочная печать
        if state == 2:
            self.twitch_cookies_edit.show()
        else:
            self.twitch_cookies_edit.hide()
        self.adjustSize()  # Обновляем размер окна после изменения видимости элемента

    def save_account(self):
        user_id = get_user_id()
        if user_id is None:
            QMessageBox.critical(self, "Error", "User ID is not set. Please login again.")
            return

        twitch_cookies = self.twitch_cookies_edit.toPlainText() if self.use_twitch_cookies_checkbox.isChecked() else "default cookies"

        data = {
            'user_id': user_id,
            'name': self.account_name_edit.text(),
            'cookies': self.cookies_edit.toPlainText(),
            'twitch_cookies': twitch_cookies,
            'messages': self.messages_edit.toPlainText()
        }
        response = requests.post('http://77.232.131.189:5000/add_kick_account', json=data)
        if response.status_code == 200:
            QMessageBox.information(self, "Success", "Account successfully added.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to add account. Server responded with an error.")
  
class AccountManager:
    def __init__(self, data_fetcher_thread):
        self.data_fetcher_thread = data_fetcher_thread
        self.active_drivers_count = 0
        self.account_widgets = []
        self.lock = Lock()

    def add_account_widget(self, account_widget):
        self.account_widgets.append(account_widget)

    def on_chat_writer_started(self):
        with self.lock:
            self.active_drivers_count += 1
            if self.active_drivers_count == 1:
                self.data_fetcher_thread.start_parser()

    def on_chat_writer_stopped(self):
        with self.lock:
            self.active_drivers_count -= 1
            if self.active_drivers_count == 0:
                self.data_fetcher_thread.stop_parser()

    def are_drivers_running(self):
        with self.lock:
            return any(widget.is_running() for widget in self.account_widgets)

    def log_active_drivers_count(self):
        with self.lock:
            running_count = sum(widget.is_running() for widget in self.account_widgets)
            print(f"Active drivers count: {running_count}")

    def process_message(self, message):
        if 'Раздача поинтов началась.' in message:
            for widget in self.account_widgets:
                if widget.thread and widget.thread.isRunning():
                    widget.thread.set_wg_active(True)
            print(f"Запуск WG сообщения...")

        if 'Починка' in message:
            for widget in self.account_widgets:
                if widget.thread and widget.thread.isRunning():
                    widget.thread.send_message_signal.emit('pochinka')
            print(f"Починка началась...")

class ShopParserThread(QThread):
    def __init__(self, account_name, twitch_cookies, product, parent=None):
        super(ShopParserThread, self).__init__(parent)
        self.account_name = account_name
        self.twitch_cookies = twitch_cookies
        self.product = product
        self.is_running = True

    def run(self):
        try:
            with self.get_chromedriver() as self.driver:
                if not self.driver:
                    print(f'Не удалось инициализировать драйвер Chrome [{self.account_name}]')
                    return
                print(f'Окно браузера запущено. [{self.account_name}]')


                site1 = f'https://www.twitch.tv/kishimy2'
                site2 = f'https://www.wrewards.com'
                
                self.driver.get(site1)
                self.add_cookies()
                time.sleep(1)
                self.driver.get(site1)
                time.sleep(3)
                self.driver.execute_script("window.open('');")
                
                second_tab = self.driver.window_handles[1]
                self.driver.switch_to.window(second_tab)
                
                self.driver.get(site2)
                time.sleep(5)
                
                 # Логинимся в аккаунт
                try:
                    button = self.driver.find_element(By.XPATH, "//a[text()='Login']")
                    button.click()
                except NoSuchElementException:
                    print('Кнопки login не найдено.')
                time.sleep(2)
                try:
                    button = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Log in via Twitch')]")
                    button.click()
                except NoSuchElementException:
                    print('Кнопки login2 не найдено.')
                time.sleep(3)
                

                while self.is_running:
                    # Пример: просто ждем
                    time.sleep(1)
        except Exception as e:
            print(f'Ошибка в методе run() [{self.account_name}] ')

    def get_chromedriver(self, user_agent=None):
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            if user_agent:
                chrome_options.add_argument(f'--user-agent={user_agent}')

            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument("--disable-proxy-certificate-handler")
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument("--window-size=1650,1000")

            s = Service(executable_path='chromdriver/chromedriver.exe')

            driver = webdriver.Chrome(service=s, options=chrome_options)
            
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                'source': '''
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
                '''
            })
            return driver
        except Exception as e:
            print(f'Ошибка при инициализации Chromedriver: {e}')
            return None

    def add_cookies(self):
        try:
            cookies = json.loads(self.twitch_cookies)
            for cookie in cookies:
                if 'expirationDate' in cookie:
                    cookie['expiry'] = int(cookie['expirationDate'])
                    del cookie['expirationDate']
                if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                    cookie['sameSite'] = 'None'
                self.driver.add_cookie(cookie)
        except Exception as e:
            print(f'Ошибка при добавлении кук: {e}')

    def stop(self):
        self.is_running = False
        self.driver.quit()
        print(f'Поток {self.account_name} остановлен')
        
class SelectProductDialog(QDialog):
    def __init__(self, parent=None):
        super(SelectProductDialog, self).__init__(parent)
        self.setWindowTitle("Выберите товар")
        self.setGeometry(100, 100, 300, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("""
            QDialog {
                background-color: #333;
                color: white;
            }
            QListWidget {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                margin-top: 5px;
                margin-bottom: 5px;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #555;
                color: white;
                border: 1px solid #666;
                padding: 5px;
                margin: 5px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)

        self.product_list = QListWidget(self)
        products = ['200$ etf', '200$ ltc', '100$ steam gift', '100$ amazon gift']
        self.product_list.addItems(products)
        layout.addWidget(self.product_list)

        self.select_button = QPushButton("Выбрать", self)
        self.select_button.clicked.connect(self.select_product)
        layout.addWidget(self.select_button)

    def select_product(self):
        selected_items = self.product_list.selectedItems()
        if selected_items:
            self.selected_product = selected_items[0].text()
            self.accept()

    def get_selected_product(self):
        return getattr(self, 'selected_product', None)
                
class ShopAccountWidget(QWidget):
    def __init__(self, account_id, account_name, twitch_cookies, parent=None):
        super().__init__(parent)
        self.account_id = account_id
        self.account_name = account_name
        self.twitch_cookies = twitch_cookies
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        self.setMinimumHeight(50)
        self.setStyleSheet("QWidget { margin-left: 10px; border-radius: 3px; }")

        font_large = QFont()
        font_large.setFamilies([u"Gotham Pro Black"])
        font_large.setPointSize(14)

        self.account_label = QLabel(self.account_name)
        self.account_label.setFont(font_large)
        layout.addWidget(self.account_label, 4)

        self.select_product_button = QPushButton("Выбрать товар")
        self.select_product_button.setStyleSheet("QPushButton { padding: 5px; border-radius: 3px; }")
        layout.addWidget(self.select_product_button, 1)
        self.select_product_button.clicked.connect(self.select_product)

        self.start_button = QPushButton("Запустить")
        self.start_button.setStyleSheet("QPushButton { padding: 5px; border-radius: 3px; }")
        layout.addWidget(self.start_button, 1)
        self.start_button.clicked.connect(self.start_parser)

        self.setLayout(layout)

    def select_product(self):
        dialog = SelectProductDialog(self)
        if dialog.exec() == QDialog.Accepted:
            selected_product = dialog.get_selected_product()
            if selected_product:
                self.select_product_button.setText(selected_product)

    def start_parser(self):
        self.thread = ShopParserThread(self.account_name, self.twitch_cookies, self.select_product_button.text())
        self.thread.start()
      
class ShopParserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Парсер магазина")
        self.setGeometry(100, 100, 550, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.init_ui()
        self.load_accounts()
        self.old_pos = None
        self.center_on_screen()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        self.setStyleSheet("""
        QWidget {
            background-color: #333;
            color: white;
            margin: 2px;
            border-radius: 3px;
        }
        QPushButton {
            background-color: #555;
            color: white;
            border: 1px solid #666;
            padding: 5px;
            margin: 5px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #777;
        }
        QListWidget {
            background-color: #2b2b2b;
            border: none;
            border-radius: 5px;
        }
        """)

        self.header = QWidget(self)
        self.header.setFixedHeight(40)
        self.header.setStyleSheet("background-color: #444; border-radius: 5px;")
        layout.addWidget(self.header)

        self.close_button = QPushButton("X", self.header)
        self.close_button.setStyleSheet("QPushButton { color: red; font-weight: bold; border-radius: 5px; }")
        self.close_button.clicked.connect(self.close)
        self.close_button.setGeometry(485, 5, 40, 30)

        self.account_list = QListWidget()
        layout.addWidget(self.account_list)

    def load_accounts(self):
        user_id = get_user_id()
        if user_id is None:
            print("User ID is not set. Cannot load accounts.")
            return

        self.account_list.clear()  # Очищаем список перед загрузкой новых аккаунтов

        try:
            response = requests.get('http://77.232.131.189:5000/get_kick_accounts', params={'user_id': user_id})
            if response.status_code == 200:
                accounts_data = response.json()
                accounts = accounts_data.get('accounts', [])
                for account in accounts:
                    self.add_account_to_list(account['id'], account['name'], account.get('twitch_cookies', ''))
            else:
                print(f"Failed to load accounts. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")

    def add_account_to_list(self, account_id, name, twitch_cookies):
        account_widget = ShopAccountWidget(account_id, name, twitch_cookies, self)
        list_widget_item = QListWidgetItem(self.account_list)
        list_widget_item.setSizeHint(account_widget.sizeHint())
        self.account_list.addItem(list_widget_item)
        self.account_list.setItemWidget(list_widget_item, account_widget)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.header.rect().contains(event.position().toPoint()):
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def center_on_screen(self):
        screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())      
        
  
class AccountWidget(QWidget):
    def __init__(self, account_id, account_name, cookies, twitch_cookies, messages, manager_window, parent=None):
        super().__init__(parent)
        self.account_id = account_id
        self.account_name = account_name
        self.cookies = cookies
        self.twitch_cookies = twitch_cookies
        self.messages = messages
        self.manager_window = manager_window
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        self.setMinimumHeight(50)
        self.setStyleSheet("QWidget { margin-left: 10px; border-radius: 3px; }")

        font_large = QFont()
        font_large.setFamilies([u"Gotham Pro Black"])
        font_large.setPointSize(14)
        
        self.account_label = QLabel(self.account_name)
        self.account_label.setFont(font_large)
        layout.addWidget(self.account_label, 4)

        self.settings_button = QPushButton("Настроить")
        self.settings_button.setStyleSheet("QPushButton { padding: 5px; border-radius: 3px; }")
        layout.addWidget(self.settings_button, 1) 
        self.settings_button.clicked.connect(self.show_settings)
        
        self.delete_account_button = QPushButton("Удалить")
        self.delete_account_button.setStyleSheet("QPushButton { padding: 5px; border-radius: 3px; }")
        layout.addWidget(self.delete_account_button, 1)
        self.delete_account_button.clicked.connect(self.confirm_delete_account)

        self.setLayout(layout)

    def show_settings(self):
        dialog = AccountSettingsDialog(self.account_id, self.account_name, self.cookies, self.twitch_cookies, self.messages, self)
        if dialog.exec() == QDialog.Accepted:
            self.account_name = dialog.account_name_edit.text()
            self.cookies = dialog.cookies_edit.toPlainText()
            self.twitch_cookies = dialog.twitch_cookies_edit.toPlainText()  # Новое поле
            self.messages = dialog.messages_edit.toPlainText()
            self.account_label.setText(self.account_name)

    def confirm_delete_account(self):
        reply = QMessageBox.question(self, 'Confirm Delete', f"Are you sure you want to delete the account '{self.account_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.delete_account()

    def delete_account(self):
        user_id = get_user_id()
        if user_id is None:
            QMessageBox.critical(self, "Error", "User ID is not set. Please login again.")
            return

        data = {
            'account_id': self.account_id
        }
        response = requests.post('http://77.232.131.189:5000/delete_kick_account', json=data)
        if response.status_code == 200:
            QMessageBox.information(self, "Success", "Account successfully deleted.")
            self.manager_window.load_accounts()  # Обновляем список аккаунтов после удаления
        else:
            QMessageBox.critical(self, "Error", "Failed to delete account. Server responded with an error.")
     
class AccountManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Account Manager")
        self.setGeometry(100, 100, 450, 550) 
        self.setWindowFlags(Qt.FramelessWindowHint) 
        self.init_ui()
        self.load_accounts()
        self.old_pos = None
        self.center_on_screen()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        self.setStyleSheet("""
        QWidget {
            background-color: #333;
            color: white;
            margin: 2px;
            border-radius: 3px;
        }
        QPushButton {
            background-color: #555;
            color: white;
            border: 1px solid #666;
            padding: 5px;
            margin: 5px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #777;
        }
        QListWidget {
            background-color: #2b2b2b;
            border: none;
            border-radius: 5px;
        }
        """)

        self.header = QWidget(self)
        self.header.setFixedHeight(40)
        self.header.setStyleSheet("background-color: #444; border-radius: 5px;") 
        layout.addWidget(self.header)

        self.close_button = QPushButton("X", self.header)
        self.close_button.setStyleSheet("QPushButton { color: red; font-weight: bold; border-radius: 5px; }")
        self.close_button.clicked.connect(self.close)
        self.close_button.setGeometry(385, 5, 40, 30) 

        self.account_list = QListWidget()
        layout.addWidget(self.account_list)

        add_account_button = QPushButton("Добавить аккаунт")
        font = QFont()
        font.setFamilies([u"Gotham Pro Black"])
        font.setPointSize(12)
        add_account_button.setFont(font)
        add_account_button.clicked.connect(self.add_account)
        layout.addWidget(add_account_button)

    def add_account(self):
        dialog = AddAccountDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_accounts()

    def load_accounts(self):
        user_id = get_user_id()
        if user_id is None:
            print("User ID is not set. Cannot load accounts.")
            return

        self.account_list.clear()  # Очищаем список перед загрузкой новых аккаунтов

        try:
            response = requests.get('http://77.232.131.189:5000/get_kick_accounts', params={'user_id': user_id})
            if response.status_code == 200:
                accounts_data = response.json()
                accounts = accounts_data.get('accounts', [])
                for account in accounts:
                    self.add_account_to_list(account['id'], account['name'], account['cookies'], account['twitch_cookies'], account['messages'])
            else:
                print(f"Failed to load accounts. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")

    def add_account_to_list(self, id, name, cookies, twitch_cookies, messages):
        account_widget = AccountWidget(id, name, cookies, twitch_cookies, messages, self)
        list_widget_item = QListWidgetItem(self.account_list)
        list_widget_item.setSizeHint(account_widget.sizeHint())
        self.account_list.addItem(list_widget_item)
        self.account_list.setItemWidget(list_widget_item, account_widget)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.header.rect().contains(event.position().toPoint()):
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
    
    def center_on_screen(self):
        screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())


class DataFetcherThread(QThread):
    stream_is_start_signal = Signal(str)
    stream_is_over_signal = Signal(str)
    change_streamer_name_signal = Signal(str)
    pochinka_signal = Signal()

    def __init__(self, chat_writers, account_manager, parent=None):
        super(DataFetcherThread, self).__init__(parent)
        self.message_queue = Queue()
        self.parser_started = False
        self.account_manager = account_manager

    def run(self):
        last_processed_id = None
        print('DataFetcherThread начал работу.')

        while True:
            try:
                user_id = get_user_id()
                params = {'user_id': user_id}
                response = requests.get('http://188.225.86.91:5000/get_data', params=params)
                if response.status_code == 200:
                    data = response.json()
                    message = data.get('message')
                    message_id = data.get('id')
                    if message_id != last_processed_id:
                        last_processed_id = message_id
                        self.message_queue.put((message, message_id))
                else:
                    print(f'[DataFetcher]: Ошибка при получении данных с сервера')

                if not self.message_queue.empty():
                    message, _ = self.message_queue.get()
                    message_time = datetime.datetime.now()
                    if 'Начался стрим на канале' in message:
                        print(message)
                        split_message = message.split()
                        streamer = split_message[4]
                        self.stream_is_start_signal.emit(streamer)
                        self.change_streamer_name_signal.emit(streamer)

                    if 'передал рейд' in message:
                        print(message)
                        split_message = message.split()
                        streamer = split_message[3]
                        self.change_streamer_name_signal.emit(streamer)

                    if 'Стрим на канале' in message:
                        print(message)
                        streamer = message.split()[-1]
                        if 'Стрим на канале' in message:   
                            self.stream_is_over_signal.emit(streamer)

                    if self.account_manager.are_drivers_running():
                        self.account_manager.process_message(message)

                time.sleep(10)

            except Exception as e:
                print(e)

    def start_parser(self):
        self.parser_started = True
        print("Parser started")

    def stop_parser(self):
        self.parser_started = False
        print("Parser stopped")

    def stop(self):
        self.parser_started = False


class ChatWriterThread(QThread):
    loaded_signal = Signal()
    send_message_signal = Signal(str)
    wg_active = Signal(bool)

    def __init__(self, streamer=None, account_name='bot', cookie=None, messages=None, parent=None):
        super(ChatWriterThread, self).__init__(parent)
        self.is_running = True
        self.streamer = streamer
        self.account_name = account_name
        self.cookie = cookie
        self.send_message_signal.connect(self.send_message_on_kick)
        self.wg_active = False
        self.is_ready = False
        self.driver = None
        self.set_streamer_name()
        self.messages = messages if messages else [] 
        self.all_messages = self.messages.splitlines()
        self.random_messages_enabled = True
        
        self.sent_messages_file = f"sent_messages/sent_messages_{self.account_name}.txt"
        self.sent_messages = self.load_sent_messages()
        
    def set_random_messages_enabled(self, enabled):
        self.random_messages_enabled = enabled

    @Slot(str)
    def change_streamer_name(self, streamer):
        self.streamer = streamer
        self.set_streamer_name()

    def set_streamer_name(self):
        if self.streamer == 'WatchGamesTV':
            self.streamer_name = 'ibby'
        elif self.streamer == 'Hyuslive':
            self.streamer_name = 'hyus'
        elif self.streamer == 'WRewards':
            self.streamer_name = 'bro'
        elif self.streamer == 'pkle':
            self.streamer_name = 'pkle'
        else:
            self.streamer_name = 'bro'
                  
    def run(self):
        try:
            with self.get_chromedriver(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ) as self.driver:
                if not self.driver:
                    print(f'Не удалось инициализировать драйвер Chrome [{self.account_name}]')
                    return
                print(f'Окно браузера запущено. [{self.account_name}]')
                    
                #site = f'https://kick.com/{self.streamer}'
                site = f'https://kick.com/Suzuraya1'
                self.driver.get(site) 
                
                try:
                    button2 = self.driver.find_element(By.XPATH, '//*[@id="app"]/span/div/div[3]/button[1]')
                    button2.click()
                except NoSuchElementException:
                    print('Кнопки 1 не найдено.')
                
                self.add_cookies()
                while self.is_ready == False:
                    status = self.check_cookies(site)
                    if status:
                        self.is_ready = True
                    else:
                        self.add_cookies() 
                
                print(f'[{self.account_name}] Готов')
                self.loaded_signal.emit()  
                
                while self.is_running:
                    if self.wg_active:
                        self.send_message_on_kick('WG')
                        self.wg_active = False
                    else:
                        if self.random_messages_enabled:
                            delay = random.randint(120, 240)  # Задержка между случайными сообщениями
                            for i in range(delay):
                                #print(self.streamer_name)
                                if self.is_running and self.random_messages_enabled:
                                    time.sleep(1)
                                    if self.wg_active:
                                        break
                                else:
                                    break
                            else:
                                self.send_random_message()
                                
                    time.sleep(1)
                    
        except Exception as e:
            print(f'Ошибка в методе run() [{self.account_name}] ')

    def check_cookies(self, site):
        try:
            self.driver.get(site)
            self.avatar_element = self.driver.find_element(By.XPATH, '//*[@id="headlessui-menu-button-3"]/div/img')
            if self.avatar_element:
                return True   
        except NoSuchElementException:
            print(f'Аватарка не найдена. [{self.account_name}]')
        return False
        
    def add_cookies(self):
        try:
            cookies = json.loads(self.cookie)
            for cookie in cookies:
                if 'expirationDate' in cookie:
                    cookie['expiry'] = int(cookie['expirationDate'])
                    del cookie['expirationDate']
                if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                    cookie['sameSite'] = 'None'
                self.driver.add_cookie(cookie)
        except Exception as e:
            print(f'Ошибка при добавлении кук: {e}')
        
    def load_sent_messages(self):
        if os.path.exists(self.sent_messages_file):
            with open(self.sent_messages_file, 'r', encoding='utf-8') as file:
                return file.read().splitlines()
        return []

    def save_sent_message(self, message):
        with open(self.sent_messages_file, 'a', encoding='utf-8') as file:
            file.write(message + '\n')
       
    def send_random_message(self):
        unsent_messages = [msg for msg in self.all_messages if self.sent_messages.count(msg) < self.all_messages.count(msg)]
        
        if not unsent_messages:
            self.sent_messages = []
            unsent_messages = self.all_messages
            with open(self.sent_messages_file, 'w', encoding='utf-8') as file:
                file.write('')

        random_message = random.choice(unsent_messages)
        self.send_message_on_kick(random_message.format(streamer_name=self.streamer_name))
        self.save_sent_message(random_message)
        self.sent_messages.append(random_message)
        
    @Slot(str)
    def send_message_on_kick(self, message):
        if message == 'random' and self.wg_active:
            return
        
        try:
            self.chat_input = self.driver.find_element(By.ID, "message-input")
            if self.chat_input:
                try:
                    if message == 'WG':   
                        delay = random.randint(1, 30)
                        time.sleep(delay)
                    if message == 'pochinka':   
                        message = '!join'
                        delay = random.randint(1, 2)
                        time.sleep(delay)    
                    
                    self.chat_input.click()
                    self.chat_input.send_keys(message)
                    self.chat_input.send_keys(Keys.ENTER)
                    
                    print(f'С аккаунта {self.account_name} отправлено сообщение - {message}')
                except Exception as e:
                    print(f'Ошибка при отправке сообщения [{self.account_name}] ')
                    print(e)
            else:
                print(f'Chat input не инициализирован. [{self.account_name}]')
        except Exception as e:
            print(f'Ошибка при поиске chat_input [{self.account_name}] ')
             
    def get_chromedriver(self, user_agent=None):
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            if user_agent:
                chrome_options.add_argument(f'--user-agent={user_agent}')

            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument("--disable-proxy-certificate-handler")
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--allow-running-insecure-content')

            s = Service(executable_path='chromdriver/chromedriver.exe')

            driver = webdriver.Chrome(service=s, options=chrome_options)
            
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                'source': '''
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
                '''
            })
            return driver
        except Exception as e:
            print(f'Ошибка при инициализации Chromedriver: {e}')
            return None
                   
    
    @Slot(bool)
    def set_wg_active(self, state):
        self.wg_active = state
              
    def stop(self):
        self.is_running = False
        self.driver.quit()
        del self.driver
        print(f'Поток {self.account_name} остановлен')


class OnStartAccountWidget(QWidget):
    chat_writer_started = Signal()
    chat_writer_stopped = Signal()

    def __init__(self, streamer, account_name, cookies, messages, account_id, parent=None):
        super().__init__(parent)
        self.account_id = account_id
        self.account_name = account_name
        self.cookies = cookies
        self.messages = messages
        self.streamer = streamer
        self.init_ui()
        self.thread = None

    def init_ui(self):
        layout = QHBoxLayout(self)
        self.setMinimumHeight(50)
        self.setStyleSheet("QWidget { margin-left: 10px; border-radius: 3px; }")

        font_large = QFont()
        font_large.setFamilies([u"Gotham Pro Black"])
        font_large.setPointSize(14)

        self.account_label = QLabel(self.account_name)
        self.account_label.setFont(font_large)
        layout.addWidget(self.account_label, 4)

        self.settings_button = QPushButton("Настроить")
        self.settings_button.setStyleSheet("QPushButton { padding: 5px; border-radius: 3px; }")
        layout.addWidget(self.settings_button, 1)
        self.settings_button.clicked.connect(self.show_settings)

        self.start_chat_writer_button = QPushButton("Запустить")
        self.start_chat_writer_button.setStyleSheet("QPushButton { padding: 5px; border-radius: 3px; }")
        layout.addWidget(self.start_chat_writer_button, 1)
        self.start_chat_writer_button.clicked.connect(self.toggle_chat_writer)

        self.setLayout(layout)

    def show_settings(self):
        dialog = AccountSettingsDialog(self.account_id, self.account_name, self.cookies, self.messages, self)
        if dialog.exec() == QDialog.Accepted:
            self.account_name = dialog.account_name_edit.text()
            self.cookies = dialog.cookies_edit.toPlainText()
            self.messages = dialog.messages.edit.toPlainText()
            self.account_label.setText(self.account_name)

    @Slot()
    def toggle_chat_writer(self):
        if self.thread and self.thread.isRunning():
            self.stop_chat_writer()
        else:
            self.start_chat_writer()

    def start_chat_writer(self):
        if self.thread is None or not self.thread.isRunning():
            self.thread = ChatWriterThread(self.streamer, self.account_name, self.cookies, self.messages)
            self.thread.loaded_signal.connect(self.on_chat_writer_loaded)
            self.chat_writer_thread = self.thread
            self.thread.start()
            self.start_chat_writer_button.setText("Загрузка")
            self.chat_writer_started.emit()
        else:
            print(f'Поток для {self.account_name} уже запущен')

    def stop_chat_writer(self):
        if self.thread and self.thread.isRunning():
            self.thread.is_running = False
            self.thread.stop()
            self.start_chat_writer_button.setText("Запустить")
            self.chat_writer_stopped.emit()
            self.start_chat_writer_button.setStyleSheet("QPushButton { padding: 5px; border-radius: 3px; }")

    @Slot()
    def on_chat_writer_loaded(self):
        self.start_chat_writer_button.setText("Закрыть")
        self.start_chat_writer_button.setStyleSheet("""
            QPushButton {
                background-color: #810d0d;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #5f0c0c;
            }
        """)
        
    def toggle_random_messages(self, enabled):
        if self.thread and self.thread.isRunning():
            self.thread.set_random_messages_enabled(enabled)
            
    def set_random_messages_enabled(self, enabled):
        self.random_messages_enabled = enabled
        print(f'[{self.account_name}] Рандомные сообщения включены: {self.random_messages_enabled}')

    def is_running(self):
        return self.start_chat_writer_button.text() == "Закрыть"
        
class OnStartAccountManagerWindow(QMainWindow):
    def __init__(self, streamer=None, account_manager=None):
        super().__init__()
        self.streamer = streamer
        self.setWindowTitle("Account Manager")
        self.setGeometry(100, 100, 450, 550)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.init_ui()
        self.old_pos = None
        self.center_on_screen()
        self.account_manager = account_manager
        self.load_accounts()
        self.chat_writer_threads = []
        self.all_writers_started = False

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        self.setStyleSheet("""
        QWidget {
            background-color: #333;
            color: white;
            margin: 2px;
            border-radius: 3px;
        }
        QPushButton {
            background-color: #555;
            color: white;
            border: 1px solid #666;
            padding: 5px;
            margin: 5px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #777;
        }
        QListWidget {
            background-color: #2b2b2b;
            border: none;
            border-radius: 5px;
        }
        """)

        self.header = QWidget(self)
        self.header.setFixedHeight(40)
        self.header.setStyleSheet("background-color: #444; border-radius: 5px;")
        layout.addWidget(self.header)

        self.close_button = QPushButton("X", self.header)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #810d0d;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5f0c0c;
            }
        """)
        self.close_button.clicked.connect(self.close)
        self.close_button.setGeometry(385, 5, 40, 30)

        self.account_list = QListWidget()
        layout.addWidget(self.account_list)
        
        font = QFont()
        font.setPointSize(12)

        self.start_all_writers_button = QPushButton("Запустить все")
        self.start_all_writers_button.setFont(font)
        self.start_all_writers_button.setCheckable(True)
        self.start_all_writers_button.setChecked(False)
        self.start_all_writers_button.clicked.connect(self.toble_start_all_writers)
        layout.addWidget(self.start_all_writers_button)

        self.toggle_random_messages_button = QPushButton("Включить рандомные сообщения", self)
        self.toggle_random_messages_button.setFont(font)
        self.toggle_random_messages_button.setCheckable(True)
        self.toggle_random_messages_button.setChecked(False)
        self.toggle_random_messages_button.clicked.connect(self.toggle_random_messages)
        layout.addWidget(self.toggle_random_messages_button)

    def toggle_random_messages(self):
        self.random_messages_enabled = self.toggle_random_messages_button.isChecked()
        if self.random_messages_enabled:
            print(f'Рандомные сообщения включены: {self.random_messages_enabled}')
            for index in range(self.account_list.count()):
                item = self.account_list.item(index)
                widget = self.account_list.itemWidget(item)
                widget.toggle_random_messages(True)
                self.toggle_random_messages_button.setText("Выключить рандомные сообщения")
        else:
            print(f'Рандомные сообщения включены: {self.random_messages_enabled}')
            for index in range(self.account_list.count()):
                item = self.account_list.item(index)
                widget = self.account_list.itemWidget(item)
                widget.toggle_random_messages(False)
                self.toggle_random_messages_button.setText("Включить рандомные сообщения")  

    def toble_start_all_writers(self):
        self.all_writers_started = self.start_all_writers_button.isChecked()
        if self.all_writers_started:
            self.start_all_writers_button.setText('Закрыть все')
            self.start_all_writers()
        else:
            self.start_all_writers_button.setText('Запустить все')
            self.stop_all_writers()

    def start_all_writers(self):
        for index in range(self.account_list.count()):
            item = self.account_list.item(index)
            widget = self.account_list.itemWidget(item)
            widget.toggle_chat_writer()
            
    def stop_all_writers(self):
        for index in range(self.account_list.count()):
            item = self.account_list.item(index)
            widget = self.account_list.itemWidget(item)
            widget.toggle_chat_writer()

    def load_accounts(self):
        user_id = get_user_id()
        if user_id is None:
            print("User ID is not set. Cannot load accounts.")
            return

        self.account_list.clear() 

        try:
            response = requests.get('http://77.232.131.189:5000/get_kick_accounts', params={'user_id': user_id})
            if response.status_code == 200:
                accounts_data = response.json()
                accounts = accounts_data.get('accounts', [])
                for account in accounts:
                    self.add_account_to_list(account['name'], account['cookies'], account['messages'])
            else:
                print(f"Failed to load accounts. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")

    def add_account_to_list(self, name, cookies, messages):
        account_widget = OnStartAccountWidget(self.streamer, name, cookies, messages, self)
        account_widget.chat_writer_started.connect(self.account_manager.on_chat_writer_started)
        account_widget.chat_writer_stopped.connect(self.account_manager.on_chat_writer_stopped)
        list_widget_item = QListWidgetItem(self.account_list)
        list_widget_item.setSizeHint(account_widget.sizeHint())
        self.account_list.addItem(list_widget_item)
        self.account_list.setItemWidget(list_widget_item, account_widget)
        self.account_manager.add_account_widget(account_widget)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.header.rect().contains(event.position().toPoint()):
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def center_on_screen(self):
        screen_geometry = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())


class MainApp(QMainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        normal_cursor_path = 'cursor/Glib Cur v3 (Rounded)/Normal Select.cur'
        normal_cursor_pixmap = QtGui.QPixmap(normal_cursor_path)
        normal_cursor = QtGui.QCursor(normal_cursor_pixmap, 0, 0)
        self.setCursor(normal_cursor)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.size())
        self.old_pos = self.pos()

        self.ui.login_error_text.hide()
        self.ui.close_button.clicked.connect(self.close_button_act)
        self.ui.wrap_button.clicked.connect(self.wrap_button_act)
        self.ui.login_button.clicked.connect(self.check_login)
        self.ui.pass_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.add_buttons_style()

        self.show_login_frame()

        self.ui.hyus_icon = self.wrap_with_frame(self.ui.hyus_icon, "images/hyus.png")
        self.ui.pkle_icon = self.wrap_with_frame(self.ui.pkle_icon, "images/pkle.png")
        self.ui.wrewards_icon = self.wrap_with_frame(self.ui.wrewards_icon, "images/wrewards.png")
        self.ui.ibby_icon = self.wrap_with_frame(self.ui.ibby_icon, "images/ibby.png")

        self.streamer = None
        self.streamer_frames = [self.ui.hyus_icon, self.ui.pkle_icon, self.ui.wrewards_icon, self.ui.ibby_icon]
        self.ui.hyus_icon.clicked.connect(lambda: self.change_streamer('Hyuslive'))
        self.ui.pkle_icon.clicked.connect(lambda: self.change_streamer('pkle'))
        self.ui.wrewards_icon.clicked.connect(lambda: self.change_streamer('WRewards'))
        self.ui.ibby_icon.clicked.connect(lambda: self.change_streamer('WatchGamesTV'))

        self.ui.item_accounts.clicked.connect(self.open_account_manager)
        self.ui.start_button.clicked.connect(self.start_button_act)
        self.show_login_frame()

        self.credentials_file = 'credentials.json'
        if self.load_credentials():
            print("Пропускаю дальше")
            self.show_main_menu()
        else:
            print('Надо залогиниться')

        self.threads = None

        self.data_fetcher_thread = DataFetcherThread(self.threads, None, self)
        self.account_manager = AccountManager(self.data_fetcher_thread)
        self.data_fetcher_thread.account_manager = self.account_manager
        

        self.data_fetcher_thread.stream_is_start_signal.connect(self.stream_is_start)
        self.data_fetcher_thread.stream_is_over_signal.connect(self.stop_all_drivers)
        self.data_fetcher_thread.change_streamer_name_signal.connect(self.change_streamer_name)
        self.data_fetcher_thread.start()
        
        self.ui.item_shop.clicked.connect(self.open_shop_parser)
        
    def open_shop_parser(self):
        self.shop_parser_window = ShopParserWindow()
        self.shop_parser_window.show()

    def open_account_manager(self):
        self.account_manager_window = AccountManagerWindow()
        self.account_manager_window.show()

    def start_button_act(self):
        if self.streamer is not None:
            self.ui.start_button_error_text.hide()
            print(self.streamer)
            self.on_start_account_manager_window = OnStartAccountManagerWindow(self.streamer, self.account_manager)
            self.on_start_account_manager_window.show()
        else:
            self.ui.start_button_error_text.show()

    @Slot(str)
    def stream_is_start(self, streamer):
        self.change_streamer(streamer)
        self.on_start_account_manager_window = OnStartAccountManagerWindow(self.streamer, self.account_manager)
        self.on_start_account_manager_window.show()
        self.on_start_account_manager_window.start_all_writers()
        
    @Slot(str)
    def stop_all_drivers(self, streamer):
        print(f"Получен сигнал о завершении стрима для {streamer}. Останавливаем все драйверы.")
        for widget in self.account_manager.account_widgets:
            if widget.thread and widget.thread.isRunning():
                widget.thread.stop()
            
    @Slot(str)
    def change_streamer_name(self, streamer):
        print(f"Стрим на канале {self.streamer} закончился, меняем имя стримера на {streamer}.")
        for widget in self.account_manager.account_widgets:
            if widget.thread and widget.thread.isRunning():
                widget.thread.change_streamer_name(streamer)

    def replace_with_clickable(self, label, image_path):
        clickable_label = ClickableLabel(label.parent())
        clickable_label.setGeometry(label.geometry())
        clickable_label.setPixmap(QtGui.QPixmap(image_path))
        clickable_label.setScaledContents(True)
        clickable_label.setAlignment(label.alignment())
        clickable_label.setFrameShape(label.frameShape())
        clickable_label.setObjectName(label.objectName())
        label.deleteLater()
        return clickable_label
    
    def wrap_with_frame(self, label, image_path):
        frame = ClickableFrame(label.parent())
        frame.setGeometry(label.geometry())
        frame.setObjectName(label.objectName())
        frame.setStyleSheet("background: transparent; padding: 2px;")

        frame.label.setGeometry(0, 0, label.width(), label.height())
        frame.label.setPixmap(QtGui.QPixmap(image_path))
        frame.label.setScaledContents(True)
        frame.label.setAlignment(label.alignment())
        frame.label.setFrameShape(label.frameShape())

        return frame
    
    def change_streamer(self, streamer):
        if streamer == 'Hyuslive':
            frame = self.ui.hyus_icon
        if streamer == 'pkle':
            frame = self.ui.pkle_icon
        if streamer == 'WRewards':
            frame = self.ui.wrewards_icon
        if streamer == 'WatchGamesTV':
            frame = self.ui.ibby_icon
            
        self.streamer = streamer
            
        for f in self.streamer_frames:
            f.setGraphicsEffect(None)
        shadow = QGraphicsDropShadowEffect(frame)
        shadow.setBlurRadius(10)
        shadow.setColor(Qt.white)
        shadow.setOffset(0, 0)
        frame.setGraphicsEffect(shadow)
 
    def show_login_frame(self):
        self.ui.item_accounts.hide()
        self.ui.item_calendar.hide()
        self.ui.item_devices.hide()
        self.ui.item_messages.hide()
        self.ui.item_shop.hide()
        self.ui.item_points.hide()
        self.ui.hyus_border.hide()
        self.ui.hyus_icon.hide()
        self.ui.pkle_border.hide()
        self.ui.pkle_icon.hide()
        self.ui.wrewards_border.hide()
        self.ui.wrewards_icon.hide()
        self.ui.ibby_border.hide()
        self.ui.ibby_icon.hide()
        self.ui.wrap_button_2.hide()
        self.ui.wrap_button_3.hide()
        self.ui.start_button_error_text.hide()
        self.ui.start_button.hide()
        
    def check_logged_in(self):
        try:
            with open('credentials.json', 'r') as file:
                credentials = json.load(file)
                if credentials.get('login') and credentials.get('password'):
                    return True
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return False
    
    def check_login(self):
        login = self.ui.login_input.text()
        password = self.ui.pass_input.text()
        self.login_server_response(login, password)
    
    def load_credentials(self):
        try:
            with open(self.credentials_file, 'r') as file:
                credentials = json.load(file)
                login = credentials['username']
                password = credentials['password']
                self.login_server_response(login, password)
                return True
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
    def save_credentials(self, username, password, user_id):
        with open(self.credentials_file, 'w') as file:
            json.dump({'username': username, 'password': password, 'user_id': user_id}, file)
            
    def login_server_response(self, login, password):
        response = requests.post('http://77.232.131.189:5000/check_login', json={'login': login, 'password': password})
        if response.status_code == 200:
            data = response.json()
            if data.get('result'):
                global current_user_id
                current_user_id = data.get('user_id') 
                print(current_user_id)
                self.ui.login_error_text.hide()
                print("Login successful!")
                self.save_credentials(login, password, current_user_id)
                self.show_main_menu()
            else:
                self.ui.login_error_text.show()
                print("Login failed!")
        else:
            QMessageBox.critical(self, "Login Error", "Failed to connect to the server.")
            
    def delete_credentials(self):
        try:
            os.remove(self.credentials_file)
        except OSError:
            pass

    def show_main_menu(self):
        self.ui.login_frame.hide()
        self.ui.login_error_text.hide()
        
        self.ui.item_accounts.show()
        self.ui.item_calendar.show()
        self.ui.item_devices.show()
        self.ui.item_messages.show()
        self.ui.item_shop.show()
        self.ui.item_points.show()
        self.ui.hyus_icon.show()
        self.ui.pkle_icon.show()
        self.ui.wrewards_icon.show()
        self.ui.ibby_icon.show()
        self.ui.wrap_button_2.show()
        self.ui.wrap_button_3.show()
        self.ui.start_button.show()
        
    def add_buttons_style(self):
        self.ui.login_button.setStyleSheet("""
            QPushButton {
                background: #ffd17a;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #ffc048;
            }
        """)
        self.ui.start_button.setStyleSheet("""
            QPushButton {
                background: #ffae00;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #d79300;
            }
        """) 
        
    def mousePressEvent(self, event):
            if event.buttons() == Qt.LeftButton:
                self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
    
    def close_button_act(self):
        self.close()      
    
    def wrap_button_act(self):
        self.showMinimized()
        
    def closeEvent(self, event):
        # Закрываем все дочерние окна перед закрытием главного окна
        try:
            if self.account_manager_window:
                self.account_manager_window.close()
        except:
            pass
        try:
            if self.on_start_account_manager_window:
                self.on_start_account_manager_window.close()
        except:
            pass

        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    
    sys.exit(app.exec())