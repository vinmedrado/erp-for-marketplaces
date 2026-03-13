# main_window_minimal.py
import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QInputDialog
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt

import psycopg2
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

# DB
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# Integrações
from integrations.mercadolivre.auth import generate_auth_link, exchange_code_for_token
from integrations.mercadolivre.api import get_items
from suppliers.wedrop import wedrop_catalog

# --------------------- FUNÇÃO DB ---------------------
def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# --------------------- ABA DE MARKETPLACE ---------------------
class MarketplaceTab(QWidget):
    def __init__(self, name: str, color: str, actions: dict):
        super().__init__()
        self.name = name
        self.color = color
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Status
        self.status_label = QLabel("Status: 🔴 Não conectado")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {color};
            background-color: #1F1F1F;
            padding: 6px;
            border-radius: 5px;
            font-weight: bold;
        """)
        layout.addWidget(self.status_label)

        # Botões
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        for label, func in actions.items():
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                background-color: {color};
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 5px;
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(func)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

# --------------------- MAIN WINDOW ---------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini ERP - Minimal")
        self.resize(900, 650)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Seletor de cliente
        self.cliente_select = QComboBox()
        new_cliente_btn = QPushButton("Novo Cliente")
        new_cliente_btn.setStyleSheet("""
            padding: 4px 12px;
            background-color: #0070C0;
            color: white;
            border-radius: 5px;
        """)
        new_cliente_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_cliente_btn.clicked.connect(self.create_new_cliente)

        cliente_layout = QHBoxLayout()
        cliente_layout.addWidget(QLabel("Cliente:"))
        cliente_layout.addWidget(self.cliente_select)
        cliente_layout.addWidget(new_cliente_btn)
        main_layout.addLayout(cliente_layout)

        # Abas
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab:selected {background: #0070C0; color: white; font-weight: bold;}
            QTabBar::tab:!selected {background: #2E2E2E; color: #CCCCCC; font-weight: normal;}
        """)

        self.ml_tab = MarketplaceTab(
            "Mercado Livre", "#FFAA00",
            actions={
                "Atualizar Tokens": self.update_ml_tokens,
                "Listar Produtos": self.list_ml_items
            }
        )

        self.wedrop_tab = MarketplaceTab(
            "Wedrop", "#28A745",
            actions={
                "Baixar Catálogo": self.download_wedrop
            }
        )

        self.tabs.addTab(self.ml_tab, "Mercado Livre")
        self.tabs.addTab(self.wedrop_tab, "Wedrop")
        main_layout.addWidget(self.tabs)

        # Log minimalista
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("""
            background-color: #1E1E1E;
            color: #E0E0E0;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            border: 1px solid #555555;
        """)
        main_layout.addWidget(self.log)

        self.setLayout(main_layout)

        # Carrega clientes
        self.load_clientes()

    # --------------------- LOG ---------------------
    def append_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {message}")
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    # --------------------- CLIENTES ---------------------
    def load_clientes(self):
        self.cliente_select.clear()
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nome FROM clientes ORDER BY nome")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            self.clientes = {str(row[0]): row[1] for row in rows}
            for id_, nome in self.clientes.items():
                self.cliente_select.addItem(nome, userData=id_)
            self.append_log(f"[INFO] {len(rows)} cliente(s) carregado(s)")
        except Exception as e:
            self.append_log(f"[ERROR] Falha ao carregar clientes: {e}")

    def create_new_cliente(self):
        nome, ok = QInputDialog.getText(self, "Novo Cliente", "Digite o nome do cliente:")
        if not ok or not nome:
            return
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO clientes (nome) VALUES (%s) RETURNING id", (nome,))
            cliente_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            self.append_log(f"[INFO] Cliente '{nome}' criado com ID {cliente_id}")
            self.load_clientes()
            self.cliente_select.setCurrentIndex(self.cliente_select.count()-1)
        except Exception as e:
            self.append_log(f"[ERROR] Falha ao criar cliente: {e}")

    # --------------------- MERCADO LIVRE ---------------------
    def update_ml_tokens(self):
        cliente_id = self.cliente_select.currentData()
        try:
            link = generate_auth_link(cliente_id)
            self.append_log(f"[ML] Abra este link e obtenha o code: {link}")
            code, ok = QInputDialog.getText(self, "Code ML", "Cole o code TG- obtido:")
            if ok and code:
                data = exchange_code_for_token(cliente_id, code)
                self.append_log(f"[ML] Tokens atualizados: {data}")
        except Exception as e:
            self.append_log(f"[ML ERROR] {e}")

    def list_ml_items(self):
        cliente_id = self.cliente_select.currentData()
        self.append_log(f"[ML] Buscando itens do cliente {self.cliente_select.currentText()}...")
        try:
            items = get_items(cliente_id)
            count = len(items.get("results", []))
            self.append_log(f"[ML] Total de produtos: {count}")
        except Exception as e:
            self.append_log(f"[ML ERROR] {e}")

    # --------------------- WEDROP ---------------------
    def download_wedrop(self):
        cliente_id = self.cliente_select.currentData()
        self.append_log(f"[Wedrop] Baixando catálogo do cliente {self.cliente_select.currentText()}...")
        try:
            wedrop_catalog(cliente_id)
            self.append_log(f"[Wedrop] Catálogo baixado com sucesso")
        except Exception as e:
            self.append_log(f"[Wedrop ERROR] {e}")

# --------------------- EXEC ---------------------
def run():
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())