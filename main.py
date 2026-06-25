import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

# Carrega o .env da raiz do Boxio antes de importar módulos que leem variáveis
# de ambiente, principalmente BOXIO_LICENSE_SERVER_URL.
load_dotenv(ROOT_DIR / ".env", override=True)

from src.core.paths import ensure_app_dirs, ensure_user_database
from src.core.logger import setup_logging
from src.updater.update_manager import write_local_version
from src.licensing.license_manager import LicenseManager
from src.licensing.activation_dialog import ActivationDialog
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    ensure_app_dirs()
    ensure_user_database()
    setup_logging()
    write_local_version()
    app = QApplication(sys.argv)
    app.setApplicationName("Boxio")
    app.setOrganizationName("Boxio")
    # Define uma fonte base válida em pontos.
    # Evita o aviso "QFont::setPointSize: Point size <= 0 (-1)" em ambientes
    # onde a fonte padrão do Qt pode retornar tamanho indefinido.
    preferred_font = "Segoe UI"
    available_families = set(QFontDatabase.families())
    if preferred_font not in available_families:
        preferred_font = "Arial"
    base_font = QFont(preferred_font)
    base_font.setPointSize(10)
    app.setFont(base_font)

    # Licenciamento comercial anual.
    # O sistema só abre após ativação/validação da licença. Em modo offline,
    # a liberação depende da tolerância definida em BOXIO_LICENSE_OFFLINE_GRACE_DAYS.
    license_manager = LicenseManager()
    license_status = license_manager.ensure_valid()
    if not license_status.allowed:
        dialog = ActivationDialog(license_manager, license_status.message)
        if dialog.exec() != ActivationDialog.Accepted:
            sys.exit(0)

    window = MainWindow()
    window.resize(1280, 780)
    window.show()
    sys.exit(app.exec())
