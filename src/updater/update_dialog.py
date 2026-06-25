"""Diálogo visual de atualização para PySide6."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit
from PySide6.QtCore import Qt


class UpdateAvailableDialog(QDialog):
    def __init__(self, manifest, parent=None):
        super().__init__(parent)
        self.manifest = manifest
        self.setWindowTitle("Atualização disponível")
        self.setModal(True)
        self.resize(560, 360)
        layout = QVBoxLayout(self)
        title = QLabel(f"Nova versão disponível: {manifest.latest_version}")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        layout.addWidget(title)
        notes = QTextEdit(); notes.setReadOnly(True)
        notes.setText("\n".join(f"• {n}" for n in manifest.notes) or "Sem notas de versão informadas.")
        layout.addWidget(notes)
        row = QHBoxLayout()
        self.manual_btn = QPushButton("Baixar manualmente")
        self.auto_btn = QPushButton("Preparar atualização")
        self.later_btn = QPushButton("Depois")
        self.auto_btn.setObjectName("primaryButton")
        row.addWidget(self.manual_btn); row.addWidget(self.auto_btn); row.addStretch(); row.addWidget(self.later_btn)
        layout.addLayout(row)
        self.later_btn.clicked.connect(self.reject)
