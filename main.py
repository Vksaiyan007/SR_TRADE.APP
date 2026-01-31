"""
SR TRADE - Professional Trading Application
Version: 2.0
Developer: SR Analytics
"""
import sys
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import *
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import mplfinance as mpf
import yfinance as yf
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============================================
# DATABASE MANAGER
# ============================================
class DatabaseManager:
    def __init__(self):
        self.db_path = "sr_trade.db"
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                stop_loss REAL,
                target_price REAL,
                trade_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_date TIMESTAMP,
                expiry_date DATE,
                strike_price REAL,
                option_type TEXT,
                strategy TEXT,
                notes TEXT,
                status TEXT DEFAULT 'OPEN',
                pnl REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Watchlist table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                UNIQUE(user_id, symbol)
            )
        ''')
        
        # Market data cache
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_cache (
                symbol TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=()):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        return result
    
    def get_trades(self, user_id=None):
        if user_id:
            return self.execute_query(
                "SELECT * FROM trades WHERE user_id = ? ORDER BY trade_date DESC",
                (user_id,)
            )
        return self.execute_query("SELECT * FROM trades ORDER BY trade_date DESC")
    
    def add_trade(self, trade_data):
        query = '''
            INSERT INTO trades (user_id, symbol, trade_type, quantity, entry_price, 
            stop_loss, target_price, expiry_date, strike_price, option_type, strategy, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        return self.execute_query(query, (
            trade_data['user_id'],
            trade_data['symbol'],
            trade_data['trade_type'],
            trade_data['quantity'],
            trade_data['entry_price'],
            trade_data.get('stop_loss'),
            trade_data.get('target_price'),
            trade_data.get('expiry_date'),
            trade_data.get('strike_price'),
            trade_data.get('option_type'),
            trade_data.get('strategy'),
            trade_data.get('notes')
        ))
    
    def update_trade(self, trade_id, exit_price):
        query = '''
            UPDATE trades 
            SET exit_price = ?, exit_date = CURRENT_TIMESTAMP, status = 'CLOSED',
                pnl = (exit_price - entry_price) * quantity * 
                      CASE WHEN trade_type = 'BUY' THEN 1 ELSE -1 END
            WHERE id = ?
        '''
        return self.execute_query(query, (exit_price, trade_id))

# ============================================
# CHART WIDGETS
# ============================================
class CandleStickChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        self.data = None
    
    def plot_candlestick(self, df, title="Price Chart"):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if len(df) > 0:
            mpf.plot(df, type='candle', style='charles', 
                    title=title, ylabel='Price',
                    ax=ax, show_nontrading=True)
        
        self.canvas.draw()
    
    def plot_line(self, x_data, y_data, label="Line", color='blue'):
        self.ax.clear()
        self.ax.plot(x_data, y_data, label=label, color=color)
        self.ax.legend()
        self.ax.grid(True, alpha=0.3)
        self.canvas.draw()

class TechnicalIndicatorChart(QWidget):
    def __init__(self):
        super().__init__()
        self.figure, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(10, 8), 
                                                                   gridspec_kw={'height_ratios': [3, 1, 1]})
        self.canvas = FigureCanvas(self.figure)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
    
    def plot_indicators(self, df):
        self.figure.clear()
        
        # Create subplots
        ax1 = self.figure.add_subplot(311)
        ax2 = self.figure.add_subplot(312)
        ax3 = self.figure.add_subplot(313)
        
        # Plot price
        ax1.plot(df.index, df['Close'], label='Close', color='blue')
        ax1.set_title('Price with Indicators')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Calculate and plot RSI
        rsi = self.calculate_rsi(df['Close'])
        ax2.plot(df.index, rsi, label='RSI', color='orange')
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5)
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5)
        ax2.set_title('RSI (14)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Calculate and plot MACD
        macd, signal, hist = self.calculate_macd(df['Close'])
        ax3.plot(df.index, macd, label='MACD', color='blue')
        ax3.plot(df.index, signal, label='Signal', color='red')
        ax3.bar(df.index, hist, label='Histogram', color='gray', alpha=0.5)
        ax3.set_title('MACD')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def calculate_rsi(self, prices, period=14):
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum()/period
        down = -seed[seed < 0].sum()/period
        rs = up/down
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100./(1.+rs)
        
        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
            
            up = (up*(period-1) + upval)/period
            down = (down*(period-1) + downval)/period
            rs = up/down
            rsi[i] = 100. - 100./(1.+rs)
        
        return rsi
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

# ============================================
# MAIN WINDOWS
# ============================================
class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("SR TRADE - Login")
        self.setGeometry(100, 100, 400, 500)
        self.setStyleSheet(self.get_style())
        
        # Center widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Logo
        logo_label = QLabel("SR TRADE")
        logo_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #2E86C1;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)
        
        # Subtitle
        subtitle = QLabel("Professional Trading Platform")
        subtitle.setStyleSheet("font-size: 14px; color: #7F8C8D; margin-bottom: 30px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Login Form
        form_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setMinimumHeight(40)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(40)
        
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        
        layout.addLayout(form_layout)
        
        # Login Button
        login_btn = QPushButton("Login")
        login_btn.setMinimumHeight(45)
        login_btn.setStyleSheet(self.get_button_style())
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)
        
        # Register Link
        register_link = QLabel("<a href='#'>Don't have an account? Register</a>")
        register_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        register_link.linkActivated.connect(self.show_register)
        layout.addWidget(register_link)
        
        central_widget.setLayout(layout)
    
    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
        
        result = self.db.execute_query(
            "SELECT id FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        
        if result:
            user_id = result[0][0]
            self.main_window = MainWindow(user_id)
            self.main_window.show()
            self.close()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")
    
    def show_register(self):
        self.register_window = RegisterWindow()
        self.register_window.show()
    
    def get_style(self):
        return """
            QMainWindow {
                background-color: #1C1C1C;
            }
            QLabel {
                color: #ECF0F1;
            }
            QLineEdit {
                background-color: #2C3E50;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #2E86C1;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3498DB;
            }
        """
    
    def get_button_style(self):
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2E86C1, stop:1 #3498DB);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498DB, stop:1 #5DADE2);
            }
        """

class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Register - SR TRADE")
        self.setGeometry(150, 150, 400, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #1C1C1C;
                color: #ECF0F1;
            }
            QLineEdit {
                background-color: #2C3E50;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Create Account")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86C1;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Form
        form_layout = QFormLayout()
        
        self.username = QLineEdit()
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.confirm_password = QLineEdit()
        
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addRow("Username:", self.username)
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Password:", self.password)
        form_layout.addRow("Confirm Password:", self.confirm_password)
        
        layout.addLayout(form_layout)
        
        # Register Button
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.register)
        layout.addWidget(register_btn)
        
        self.setLayout(layout)
    
    def register(self):
        username = self.username.text()
        email = self.email.text()
        password = self.password.text()
        confirm = self.confirm_password.text()
        
        if not all([username, email, password, confirm]):
            QMessageBox.warning(self, "Error", "All fields are required")
            return
        
        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords don't match")
            return
        
        try:
            self.db.execute_query(
                "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                (username, password, email)
            )
            QMessageBox.information(self, "Success", "Account created successfully!")
            self.close()
        except:
            QMessageBox.warning(self, "Error", "Username already exists")

class MainWindow(QMainWindow):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.db = DatabaseManager()
        self.init_ui()
        self.load_dashboard()
    
    def init_ui(self):
        self.setWindowTitle("SR TRADE - Professional Trading Platform")
        self.setGeometry(50, 50, 1400, 800)
        
        # Set app icon (placeholder)
        self.setWindowIcon(QIcon())
        
        # Set style
        self.setStyleSheet(self.get_main_style())
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout()
        central_widget.setLayout(self.main_layout)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.content_area = QStackedWidget()
        self.main_layout.addWidget(self.content_area, 1)
        
        # Status bar
        self.statusBar().showMessage(f"Welcome to SR TRADE | User ID: {self.user_id}")
    
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #2C3E50;
            }
            QPushButton {
                background-color: transparent;
                color: #ECF0F1;
                text-align: left;
                padding: 15px;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #34495E;
            }
            QPushButton:checked {
                background-color: #2E86C1;
                border-left: 4px solid #3498DB;
            }
        """)
        
        sidebar_layout = QVBoxLayout()
        
        # Logo
        logo = QLabel("SR TRADE")
        logo.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2E86C1;
            padding: 20px;
            border-bottom: 1px solid #34495E;
        """)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo)
        
        # Menu buttons
        buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("📈 Live Charts", self.show_charts),
            ("💼 Trade Journal", self.show_trades),
            ("📋 Watchlist", self.show_watchlist),
            ("🎯 Options Chain", self.show_options),
            ("📊 Analytics", self.show_analytics),
            ("⚙️ Settings", self.show_settings),
            ("📚 Education", self.show_education)
        ]
        
        self.menu_buttons = QButtonGroup(self)
        
        for text, handler in buttons:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(handler)
            self.menu_buttons.addButton(btn)
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        
        # User info
        user_info = QLabel(f"User: {self.user_id}")
        user_info.setStyleSheet("color: #95A5A6; padding: 10px; border-top: 1px solid #34495E;")
        sidebar_layout.addWidget(user_info)
        
        sidebar.setLayout(sidebar_layout)
        self.main_layout.addWidget(sidebar)
    
    def show_dashboard(self):
        self.clear_content()
        
        dashboard = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Dashboard")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86C1;")
        layout.addWidget(header)
        
        # Stats widgets
        stats_widget = QWidget()
        stats_layout = QHBoxLayout()
        
        stats = [
            ("Total Trades", "25", "#2E86C1"),
            ("Win Rate", "68%", "#27AE60"),
            ("Profit/Loss", "₹12,500", "#E74C3C"),
            ("Open Positions", "3", "#F39C12")
        ]
        
        for title, value, color in stats:
            stat_widget = QWidget()
            stat_widget.setStyleSheet(f"""
                background-color: {color};
                border-radius: 10px;
                padding: 15px;
            """)
            stat_layout = QVBoxLayout()
            
            title_label = QLabel(title)
            title_label.setStyleSheet("color: white; font-size: 14px;")
            
            value_label = QLabel(value)
            value_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
            
            stat_layout.addWidget(title_label)
            stat_layout.addWidget(value_label)
            stat_widget.setLayout(stat_layout)
            stats_layout.addWidget(stat_widget)
        
        stats_widget.setLayout(stats_layout)
        layout.addWidget(stats_widget)
        
        # Charts and Quick Trade
        content_widget = QWidget()
        content_layout = QHBoxLayout()
        
        # Chart widget
        chart_widget = CandleStickChart()
        content_layout.addWidget(chart_widget, 2)
        
        # Quick trade widget
        quick_trade = self.create_quick_trade_widget()
        content_layout.addWidget(quick_trade, 1)
        
        content_widget.setLayout(content_layout)
        layout.addWidget(content_widget)
        
        dashboard.setLayout(layout)
        self.content_area.addWidget(dashboard)
        self.content_area.setCurrentWidget(dashboard)
        
        # Load sample chart data
        self.load_sample_chart(chart_widget)
    
    def create_quick_trade_widget(self):
        widget = QWidget()
        widget.setStyleSheet("""
            background-color: #2C3E50;
            border-radius: 10px;
            padding: 20px;
        """)
        
        layout = QVBoxLayout()
        
        title = QLabel("Quick Trade")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ECF0F1;")
        layout.addWidget(title)
        
        # Symbol
        symbol_layout = QHBoxLayout()
        symbol_label = QLabel("Symbol:")
        symbol_label.setStyleSheet("color: #ECF0F1;")
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("e.g., RELIANCE, NIFTY")
        symbol_layout.addWidget(symbol_label)
        symbol_layout.addWidget(self.symbol_input)
        layout.addLayout(symbol_layout)
        
        # Trade type
        self.trade_type = QComboBox()
        self.trade_type.addItems(["BUY", "SELL"])
        layout.addWidget(QLabel("Type:"))
        layout.addWidget(self.trade_type)
        
        # Quantity
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Quantity")
        layout.addWidget(QLabel("Quantity:"))
        layout.addWidget(self.quantity_input)
        
        # Price
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Price")
        layout.addWidget(QLabel("Price:"))
        layout.addWidget(self.price_input)
        
        # Strategy
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Intraday", "Swing", "Positional", "Options", "Futures"])
        layout.addWidget(QLabel("Strategy:"))
        layout.addWidget(self.strategy_combo)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        buy_btn = QPushButton("BUY")
        buy_btn.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold;")
        buy_btn.clicked.connect(self.execute_buy)
        
        sell_btn = QPushButton("SELL")
        sell_btn.setStyleSheet("background-color: #E74C3C; color: white; font-weight: bold;")
        sell_btn.clicked.connect(self.execute_sell)
        
        btn_layout.addWidget(buy_btn)
        btn_layout.addWidget(sell_btn)
        layout.addLayout(btn_layout)
        
        widget.setLayout(layout)
        return widget
    
    def execute_buy(self):
        self.execute_trade("BUY")
    
    def execute_sell(self):
        self.execute_trade("SELL")
    
    def execute_trade(self, trade_type):
        symbol = self.symbol_input.text()
        quantity = self.quantity_input.text()
        price = self.price_input.text()
        
        if not all([symbol, quantity, price]):
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
        
        try:
            trade_data = {
                'user_id': self.user_id,
                'symbol': symbol.upper(),
                'trade_type': trade_type,
                'quantity': int(quantity),
                'entry_price': float(price),
                'strategy': self.strategy_combo.currentText()
            }
            
            self.db.add_trade(trade_data)
            QMessageBox.information(self, "Success", f"{trade_type} trade executed!")
            
            # Clear inputs
            self.symbol_input.clear()
            self.quantity_input.clear()
            self.price_input.clear()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def show_charts(self):
        self.clear_content()
        
        chart_tab = QTabWidget()
        
        # Price Chart Tab
        price_tab = QWidget()
        price_layout = QVBoxLayout()
        
        # Symbol selector
        symbol_widget = QWidget()
        symbol_layout = QHBoxLayout()
        
        symbol_label = QLabel("Symbol:")
        self.chart_symbol = QComboBox()
        self.chart_symbol.addItems(["RELIANCE", "TCS", "HDFCBANK", "INFY", "NIFTY50"])
        self.chart_symbol.currentTextChanged.connect(self.update_chart)
        
        interval_combo = QComboBox()
        interval_combo.addItems(["1d", "1h", "30m", "15m", "5m"])
        
        download_btn = QPushButton("Download Data")
        download_btn.clicked.connect(self.download_market_data)
        
        symbol_layout.addWidget(symbol_label)
        symbol_layout.addWidget(self.chart_symbol)
        symbol_layout.addWidget(QLabel("Interval:"))
        symbol_layout.addWidget(interval_combo)
        symbol_layout.addWidget(download_btn)
        
        symbol_widget.setLayout(symbol_layout)
        price_layout.addWidget(symbol_widget)
        
        # Chart display
        self.price_chart = CandleStickChart()
        price_layout.addWidget(self.price_chart)
        
        # Indicators
        indicators_widget = QWidget()
        indicators_layout = QHBoxLayout()
        
        indicators = ["RSI", "MACD", "Bollinger Bands", "Moving Averages", "Volume"]
        for indicator in indicators:
            btn = QPushButton(indicator)
            btn.clicked.connect(lambda checked, ind=indicator: self.add_indicator(ind))
            indicators_layout.addWidget(btn)
        
        indicators_widget.setLayout(indicators_layout)
        price_layout.addWidget(indicators_widget)
        
        price_tab.setLayout(price_layout)
        chart_tab.addTab(price_tab, "Price Chart")
        
        # Technical Indicators Tab
        tech_tab = TechnicalIndicatorChart()
        chart_tab.addTab(tech_tab, "Technical Indicators")
        
        self.content_area.addWidget(chart_tab)
        self.content_area.setCurrentWidget(chart_tab)
        
        # Load initial chart
        self.update_chart()
    
    def update_chart(self):
        symbol = self.chart_symbol.currentText()
        # In production, fetch real data here
        # For demo, create sample data
        self.load_sample_chart(self.price_chart, symbol)
    
    def load_sample_chart(self, chart_widget, symbol="RELIANCE"):
        # Generate sample OHLC data
        dates = pd.date_range(end=datetime.now(), periods=50, freq='D')
        np.random.seed(42)
        
        close_prices = 100 + np.cumsum(np.random.randn(50) * 2)
        open_prices = close_prices + np.random.randn(50) * 1
        high_prices = np.maximum(open_prices, close_prices) + np.random.rand(50) * 2
        low_prices = np.minimum(open_prices, close_prices) - np.random.rand(50) * 2
        volume = np.random.randint(100000, 1000000, 50)
        
        df = pd.DataFrame({
            'Open': open_prices,
            'High': high_prices,
            'Low': low_prices,
            'Close': close_prices,
            'Volume': volume
        }, index=dates)
        
        chart_widget.plot_candlestick(df, f"{symbol} - Sample Chart")
    
    def download_market_data(self):
        symbol = self.chart_symbol.currentText()
        try:
            # Using yfinance for demo - in production, use your data source
            if symbol == "NIFTY50":
                symbol = "^NSEI"
            
            data = yf.download(symbol, period="1mo", interval="1d")
            if not data.empty:
                # Cache data
                self.db.execute_query(
                    "INSERT OR REPLACE INTO market_cache (symbol, data) VALUES (?, ?)",
                    (symbol, data.to_json())
                )
                QMessageBox.information(self, "Success", f"Data downloaded for {symbol}")
                self.update_chart()
            else:
                QMessageBox.warning(self, "Error", "No data available")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Download failed: {str(e)}")
    
    def add_indicator(self, indicator):
        QMessageBox.information(self, "Indicator", f"{indicator} added to chart")
    
    def show_trades(self):
        self.clear_content()
        
        trades_widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Trade Journal")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86C1; margin-bottom: 20px;")
        layout.addWidget(header)
        
        # Toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Add Trade")
        add_btn.clicked.connect(self.add_new_trade)
        
        export_btn = QPushButton("📥 Export CSV")
        export_btn.clicked.connect(self.export_trades_csv)
        
        filter_combo = QComboBox()
        filter_combo.addItems(["All Trades", "Open Trades", "Closed Trades", "This Month"])
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search trades...")
        
        toolbar_layout.addWidget(add_btn)
        toolbar_layout.addWidget(export_btn)
        toolbar_layout.addWidget(filter_combo)
        toolbar_layout.addWidget(search_input)
        toolbar_layout.addStretch()
        
        toolbar.setLayout(toolbar_layout)
        layout.addWidget(toolbar)
        
        # Trades table
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(10)
        self.trades_table.setHorizontalHeaderLabels([
            "ID", "Symbol", "Type", "Qty", "Entry", "Exit", "SL", "Target", "Status", "P&L"
        ])
        
        # Load trades
        self.load_trades_table()
        
        layout.addWidget(self.trades_table)
        
        trades_widget.setLayout(layout)
        self.content_area.addWidget(trades_widget)
        self.content_area.setCurrentWidget(trades_widget)
    
    def load_trades_table(self):
        trades = self.db.get_trades(self.user_id)
        self.trades_table.setRowCount(len(trades))
        
        for row, trade in enumerate(trades):
            for col, value in enumerate(trade[:10]):  # First 10 columns
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.trades_table.setItem(row, col, item)
                
                # Color code P&L
                if col == 9 and value:
                    try:
                        pnl = float(value)
                        if pnl > 0:
                            item.setForeground(QColor("#27AE60"))
                        elif pnl < 0:
                            item.setForeground(QColor("#E74C3C"))
                    except:
                        pass
        
        self.trades_table.resizeColumnsToContents()
    
    def add_new_trade(self):
        dialog = TradeDialog(self.user_id, self.db)
        dialog.exec()
        self.load_trades_table()
    
    def export_trades_csv(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Trades", "", "CSV Files (*.csv)"
        )
        
        if filename:
            trades = self.db.get_trades(self.user_id)
            df = pd.DataFrame(trades, columns=[
                "ID", "User ID", "Symbol", "Type", "Quantity", "Entry Price",
                "Exit Price", "Stop Loss", "Target", "Trade Date", "Exit Date",
                "Expiry", "Strike", "Option Type", "Strategy", "Notes", "Status", "P&L"
            ])
            df.to_csv(filename, index=False)
            QMessageBox.information(self, "Success", f"Trades exported to {filename}")
    
    def show_watchlist(self):
        self.clear_content()
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Watchlist")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86C1;")
        layout.addWidget(title)
        
        # Add symbol input
        add_widget = QWidget()
        add_layout = QHBoxLayout()
        
        self.watchlist_input = QLineEdit()
        self.watchlist_input.setPlaceholderText("Enter symbol (e.g., RELIANCE)")
        
        add_btn = QPushButton("Add to Watchlist")
        add_btn.clicked.connect(self.add_to_watchlist)
        
        add_layout.addWidget(self.watchlist_input)
        add_layout.addWidget(add_btn)
        add_widget.setLayout(add_layout)
        layout.addWidget(add_widget)
        
        # Watchlist table
        self.watchlist_table = QTableWidget()
        self.watchlist_table.setColumnCount(4)
        self.watchlist_table.setHorizontalHeaderLabels(["Symbol", "LTP", "Change %", "Action"])
        
        # Load watchlist
        self.load_watchlist()
        
        layout.addWidget(self.watchlist_table)
        widget.setLayout(layout)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)
    
    def add_to_watchlist(self):
        symbol = self.watchlist_input.text().upper()
        if not symbol:
            QMessageBox.warning(self, "Error", "Please enter a symbol")
            return
        
        try:
            self.db.execute_query(
                "INSERT OR IGNORE INTO watchlist (user_id, symbol) VALUES (?, ?)",
                (self.user_id, symbol)
            )
            QMessageBox.information(self, "Success", f"{symbol} added to watchlist")
            self.watchlist_input.clear()
            self.load_watchlist()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def load_watchlist(self):
        # Sample watchlist data - in production, fetch real prices
        symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
        
        self.watchlist_table.setRowCount(len(symbols))
        
        for row, symbol in enumerate(symbols):
            # Symbol
            self.watchlist_table.setItem(row, 0, QTableWidgetItem(symbol))
            
            # Mock LTP and Change
            ltp = 1000 + row * 100
            change = (np.random.random() - 0.5) * 5
            
            self.watchlist_table.setItem(row, 1, QTableWidgetItem(f"₹{ltp:.2f}"))
            
            change_item = QTableWidgetItem(f"{change:+.2f}%")
            if change >= 0:
                change_item.setForeground(QColor("#27AE60"))
            else:
                change_item.setForeground(QColor("#E74C3C"))
            self.watchlist_table.setItem(row, 2, change_item)
            
            # Action buttons
            widget = QWidget()
            btn_layout = QHBoxLayout()
            
            chart_btn = QPushButton("📈")
            chart_btn.clicked.connect(lambda checked, s=symbol: self.chart_symbol_from_watchlist(s))
            
            trade_btn = QPushButton("💼")
            trade_btn.clicked.connect(lambda checked, s=symbol: self.trade_from_watchlist(s))
            
            remove_btn = QPushButton("❌")
            remove_btn.clicked.connect(lambda checked, s=symbol: self.remove_from_watchlist(s))
            
            btn_layout.addWidget(chart_btn)
            btn_layout.addWidget(trade_btn)
            btn_layout.addWidget(remove_btn)
            widget.setLayout(btn_layout)
            
            self.watchlist_table.setCellWidget(row, 3, widget)
    
    def chart_symbol_from_watchlist(self, symbol):
        self.chart_symbol.setCurrentText(symbol)
        self.show_charts()
    
    def trade_from_watchlist(self, symbol):
        self.symbol_input.setText(symbol)
        self.show_dashboard()
    
    def remove_from_watchlist(self, symbol):
        self.db.execute_query(
            "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?",
            (self.user_id, symbol)
        )
        self.load_watchlist()
    
    def show_options(self):
        self.clear_content()
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Options Chain")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86C1;")
        layout.addWidget(title)
        
        # Options chain widget would go here
        # For now, show placeholder
        placeholder = QLabel("Options Chain - Professional View\n\n"
                           "• Live Options Data\n• Greeks Calculator\n• Strategy Builder\n• P&L Graphs")
        placeholder.setStyleSheet("font-size: 16px; color: #7F8C8D;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)
        
        widget.setLayout(layout)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)
    
    def show_analytics(self):
        self.clear_content()
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Analytics Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86C1;")
        layout.addWidget(title)
        
        # Analytics content would go here
        placeholder = QLabel("Advanced Analytics\n\n"
                           "• Performance Metrics\n• Risk Analysis\n• Trade Statistics\n• Portfolio Health")
        placeholder.setStyleSheet("font-size: 16px; color: #7F8C8D;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)
        
        widget.setLayout(layout)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)
    
    def show_settings(self):
        self.clear_content()
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86C1;")
        layout.addWidget(title)
        
        # Settings form
        form = QFormLayout()
        
        # API Settings
        api_key = QLineEdit()
        api_key.setPlaceholderText("Enter API Key")
        api_secret = QLineEdit()
        api_secret.setPlaceholderText("Enter API Secret")
        api_secret.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Preferences
        theme_combo = QComboBox()
        theme_combo.addItems(["Dark", "Light", "System"])
        
        alert_check = QCheckBox("Enable Trade Alerts")
        alert_check.setChecked(True)
        
        form.addRow("API Key:", api_key)
        form.addRow("API Secret:", api_secret)
        form.addRow("Theme:", theme_combo)
        form.addRow("", alert_check)
        
        layout.addLayout(form)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(lambda: QMessageBox.information(self, "Settings", "Settings saved!"))
        layout.addWidget(save_btn)
        
        widget.setLayout(layout)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)
    
    def show_education(self):
        self.clear_content()
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Trading Education")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2E86C1;")
        layout.addWidget(title)
        
        # Education content
        topics = [
            ("📚 Basics of Trading", "Learn the fundamentals of stock market trading"),
            ("📈 Technical Analysis", "Chart patterns and technical indicators"),
            ("🎯 Options Trading", "Understanding calls, puts, and strategies"),
            ("📊 Risk Management", "How to manage your trading risk"),
            ("🧮 Trading Psychology", "Mindset for successful trading")
        ]
        
        for topic, desc in topics:
            topic_widget = QWidget()
            topic_layout = QHBoxLayout()
            
            topic_label = QLabel(f"<b>{topic}</b><br>{desc}")
            topic_label.setWordWrap(True)
            
            view_btn = QPushButton("Learn")
            view_btn.clicked.connect(lambda checked, t=topic: self.open_lesson(t))
            
            topic_layout.addWidget(topic_label, 1)
            topic_layout.addWidget(view_btn)
            topic_widget.setLayout(topic_layout)
            
            layout.addWidget(topic_widget)
        
        widget.setLayout(layout)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)
    
    def open_lesson(self, topic):
        QMessageBox.information(self, "Education", f"Opening lesson: {topic}")
    
    def clear_content(self):
        # Remove all widgets from content area
        while self.content_area.count():
            widget = self.content_area.widget(0)
            self.content_area.removeWidget(widget)
            if widget != self.content_area:
                widget.deleteLater()
    
    def load_dashboard(self):
        self.show_dashboard()
    
    def get_main_style(self):
        return """
            QMainWindow {
                background-color: #1C1C1C;
            }
            QLabel {
                color: #ECF0F1;
            }
            QTableWidget {
                background-color: #2C3E50;
                color: #ECF0F1;
                gridline-color: #34495E;
                border: 1px solid #34495E;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #2E86C1;
            }
            QHeaderView::section {
                background-color: #34495E;
                color: #ECF0F1;
                padding: 5px;
                border: 1px solid #2C3E50;
            }
            QComboBox, QLineEdit, QSpinBox {
                background-color: #2C3E50;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 3px;
                padding: 5px;
            }
            QTabWidget::pane {
                border: 1px solid #34495E;
                background-color: #2C3E50;
            }
            QTabBar::tab {
                background-color: #34495E;
                color: #95A5A6;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2E86C1;
                color: white;
            }
        """

class TradeDialog(QDialog):
    def __init__(self, user_id, db):
        super().__init__()
        self.user_id = user_id
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Add New Trade")
        self.setGeometry(200, 200, 500, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1C1C1C;
            }
            QLabel {
                color: #ECF0F1;
            }
        """)
        
        layout = QVBoxLayout()
        
        title = QLabel("New Trade Entry")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2E86C1;")
        layout.addWidget(title)
        
        # Form
        form = QFormLayout()
        
        self.symbol = QLineEdit()
        self.symbol.setPlaceholderText("RELIANCE, NIFTY50, etc.")
        
        self.trade_type = QComboBox()
        self.trade_type.addItems(["BUY", "SELL"])
        
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 10000)
        self.quantity.setValue(1)
        
        self.entry_price = QDoubleSpinBox()
        self.entry_price.setRange(0, 1000000)
        self.entry_price.setDecimals(2)
        
        self.stop_loss = QDoubleSpinBox()
        self.stop_loss.setRange(0, 1000000)
        self.stop_loss.setDecimals(2)
        
        self.target_price = QDoubleSpinBox()
        self.target_price.setRange(0, 1000000)
        self.target_price.setDecimals(2)
        
        self.strategy = QComboBox()
        self.strategy.addItems(["Intraday", "Swing", "Positional", "Scalping", "Options", "Futures"])
        
        self.option_type = QComboBox()
        self.option_type.addItems(["Stock", "CE", "PE"])
        
        self.expiry_date = QDateEdit()
        self.expiry_date.setDate(QDate.currentDate().addDays(30))
        
        self.strike_price = QDoubleSpinBox()
        self.strike_price.setRange(0, 1000000)
        self.strike_price.setDecimals(2)
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(100)
        
        form.addRow("Symbol:", self.symbol)
        form.addRow("Trade Type:", self.trade_type)
        form.addRow("Quantity:", self.quantity)
        form.addRow("Entry Price:", self.entry_price)
        form.addRow("Stop Loss:", self.stop_loss)
        form.addRow("Target Price:", self.target_price)
        form.addRow("Strategy:", self.strategy)
        form.addRow("Option Type:", self.option_type)
        form.addRow("Expiry Date:", self.expiry_date)
        form.addRow("Strike Price:", self.strike_price)
        form.addRow("Notes:", self.notes)
        
        layout.addLayout(form)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept_trade)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def accept_trade(self):
        trade_data = {
            'user_id': self.user_id,
            'symbol': self.symbol.text().upper(),
            'trade_type': self.trade_type.currentText(),
            'quantity': self.quantity.value(),
            'entry_price': self.entry_price.value(),
            'stop_loss': self.stop_loss.value(),
            'target_price': self.target_price.value(),
            'strategy': self.strategy.currentText(),
            'option_type': self.option_type.currentText() if self.option_type.currentText() != "Stock" else None,
            'expiry_date': self.expiry_date.date().toString("yyyy-MM-dd") if self.option_type.currentText() != "Stock" else None,
            'strike_price': self.strike_price.value() if self.option_type.currentText() != "Stock" else None,
            'notes': self.notes.toPlainText()
        }
        
        try:
            self.db.add_trade(trade_data)
            QMessageBox.information(self, "Success", "Trade added successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

# ============================================
# APP LAUNCHER
# ============================================
def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show login window
    login_window = LoginWindow()
    login_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()