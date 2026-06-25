"""Diálogo de ativação da licença anual do Boxio."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit

from src.licensing.license_manager import LicenseManager


class ActivationDialog(QDialog):
    def __init__(self, manager: LicenseManager, status_message: str = "", parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Ativação do Boxio")
        self.setModal(True)
        self.resize(560, 420)
        self.activated = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        title = QLabel("Ativação da licença Boxio")
        title.setStyleSheet("font-size:22px;font-weight:800;color:#111827;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Este software é licenciado para uso anual. Informe a chave de licença "
            "fornecida para a empresa para ativar este dispositivo."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#4B5563;")
        layout.addWidget(subtitle)

        if status_message:
            alert = QLabel(status_message)
            alert.setWordWrap(True)
            alert.setStyleSheet("background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;border-radius:10px;padding:10px;")
            layout.addWidget(alert)

        self.company = QLineEdit()
        self.company.setPlaceholderText("Nome da empresa / cliente")
        layout.addWidget(QLabel("Empresa"))
        layout.addWidget(self.company)

        self.key = QLineEdit()
        self.key.setPlaceholderText("Ex.: BOXIO-2026-XXXX-XXXX")
        layout.addWidget(QLabel("Chave de licença"))
        layout.addWidget(self.key)

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setFixedHeight(95)
        self.result.setPlaceholderText("O resultado da ativação aparecerá aqui.")
        layout.addWidget(self.result)

        buttons = QHBoxLayout()
        self.activate_btn = QPushButton("Ativar licença")
        self.activate_btn.setStyleSheet("background:#8A1CF6;color:white;border:none;border-radius:12px;padding:10px 16px;font-weight:700;")
        self.exit_btn = QPushButton("Sair")
        self.exit_btn.clicked.connect(self.reject)
        self.activate_btn.clicked.connect(self.activate)
        buttons.addWidget(self.activate_btn)
        buttons.addWidget(self.exit_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def activate(self):
        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("Validando...")
        self.result.setText("Validando licença online. Aguarde...")
        try:
            status = self.manager.activate(self.key.text(), self.company.text())
            if status.allowed:
                self.activated = True
                self.result.setText(
                    f"Licença ativada com sucesso.\n"
                    f"Status: {status.status}\n"
                    f"Validade: {status.expires_at or 'não informada'}"
                )
                self.accept()
            else:
                self.result.setText(status.message)
        finally:
            self.activate_btn.setEnabled(True)
            self.activate_btn.setText("Ativar licença")
