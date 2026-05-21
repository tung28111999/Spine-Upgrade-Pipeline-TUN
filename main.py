from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from core.pipeline import PipelineConfig, SpineUpgradePipeline

SPINE_VERSIONS = ("3.7", "3.8", "4.0", "4.1", "4.2")

APP_STYLE = """
QWidget {
    background: #0B1020;
    color: #E5E7EB;
    font-family: Segoe UI, Arial;
    font-size: 10.5pt;
}
QFrame#Card {
    background: #111827;
    border: 1px solid #263044;
    border-radius: 12px;
}
QLabel#Title {
    color: #F8FAFC;
    font-size: 20pt;
    font-weight: 700;
}
QLabel#SectionTitle {
    color: #F8FAFC;
    font-size: 12pt;
    font-weight: 650;
}
QLabel#Muted {
    color: #94A3B8;
}
QLabel#Warning {
    background: #2A1F0A;
    border: 1px solid #F59E0B;
    border-radius: 10px;
    color: #FCD34D;
    padding: 10px 12px;
    font-weight: 600;
}
QLineEdit, QComboBox {
    background: #172033;
    border: 1px solid #263044;
    border-radius: 8px;
    color: #E5E7EB;
    min-height: 36px;
    padding: 0 10px;
    selection-background-color: #3B82F6;
    selection-color: #F8FAFC;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #06B6D4;
}
QLineEdit:disabled, QComboBox:disabled {
    background: #0F172A;
    border: 1px solid #1E293B;
    color: #64748B;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox::down-arrow {
    image: url(assets/chevron-down.svg);
    width: 12px;
    height: 12px;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #111827;
    border: 1px solid #3B82F6;
    border-radius: 8px;
    color: #E5E7EB;
    outline: 0;
    padding: 4px;
    selection-background-color: #172033;
    selection-color: #06B6D4;
}
QPushButton {
    background: #172033;
    border: 1px solid #263044;
    border-radius: 8px;
    color: #E5E7EB;
    min-height: 36px;
    padding: 0 14px;
}
QPushButton:hover {
    background: #1E293B;
    border: 1px solid #06B6D4;
}
QPushButton:pressed {
    background: #0F172A;
    border: 1px solid #3B82F6;
}
QPushButton:disabled {
    background: #111827;
    border: 1px solid #1E293B;
    color: #64748B;
}
QPushButton#PrimaryButton {
    background: #7C3AED;
    border: 1px solid #7C3AED;
    color: #F8FAFC;
    font-weight: 650;
    padding: 0 20px;
}
QPushButton#PrimaryButton:hover {
    background: #8B5CF6;
    border: 1px solid #06B6D4;
}
QPushButton#PrimaryButton:pressed {
    background: #6D28D9;
    border: 1px solid #06B6D4;
}
QPushButton#PrimaryButton:disabled {
    background: #312E81;
    border: 1px solid #374151;
    color: #94A3B8;
}
QPlainTextEdit {
    background: #020617;
    border: 1px solid #263044;
    border-radius: 10px;
    color: #A7F3D0;
    font-family: Consolas, Cascadia Mono, monospace;
    font-size: 10pt;
    padding: 10px;
    selection-background-color: #064E3B;
    selection-color: #ECFDF5;
}
QProgressBar {
    background: #172033;
    border: 1px solid #263044;
    border-radius: 7px;
    color: #94A3B8;
    height: 10px;
    text-align: center;
}
QProgressBar::chunk {
    background: #06B6D4;
    border-radius: 6px;
}
QScrollBar:vertical {
    background: #0B1020;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #263044;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #3B82F6;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #0B1020;
    height: 12px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #263044;
    border-radius: 6px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #3B82F6;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QMessageBox, QFileDialog {
    background: #0B1020;
    color: #E5E7EB;
}
QMessageBox QLabel, QFileDialog QLabel {
    color: #E5E7EB;
}
QFileDialog QListView, QFileDialog QTreeView, QFileDialog QHeaderView, QFileDialog QTableView {
    background: #111827;
    alternate-background-color: #172033;
    border: 1px solid #263044;
    color: #E5E7EB;
    selection-background-color: #172033;
    selection-color: #06B6D4;
}
QToolTip {
    background: #111827;
    border: 1px solid #06B6D4;
    color: #E5E7EB;
    padding: 6px;
    border-radius: 6px;
}
"""


class PipelineWorker(QObject):
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, config: PipelineConfig) -> None:
        super().__init__()
        self.config = config

    @Slot()
    def run(self) -> None:
        try:
            pipeline = SpineUpgradePipeline(self.config, self.log.emit)
            summary = pipeline.run()
            ok = summary.failed_jobs == 0
            message = f"Done. {summary.passed_jobs} passed, {summary.failed_jobs} failed."
            self.finished.emit(ok, message)
        except Exception as exc:
            self.log.emit(f"FAIL: {exc}")
            self.finished.emit(False, str(exc))


class SpineVersionSelector(QWidget):
    def __init__(self, title: str, settings_key_prefix: str, settings: QSettings) -> None:
        super().__init__()
        self.settings_key_prefix = settings_key_prefix
        self.settings = settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("SectionTitle")
        header.addWidget(label)
        header.addStretch(1)
        self.version_combo = QComboBox()
        self.version_combo.addItems(SPINE_VERSIONS)
        self.version_combo.setFixedWidth(120)
        header.addWidget(self.version_combo)
        layout.addLayout(header)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No executable selected for this version")
        path_row.addWidget(self.path_edit, stretch=1)
        self.browse_button = QPushButton("Choose exe")
        self.browse_button.clicked.connect(self.choose_executable)
        path_row.addWidget(self.browse_button)
        layout.addLayout(path_row)

        self.version_combo.currentTextChanged.connect(self.load_path_for_version)
        self.load_path_for_version(self.version_combo.currentText())

    def executable_path(self) -> str:
        return self.path_edit.text().strip()

    def selected_version(self) -> str:
        return self.version_combo.currentText()

    def choose_executable(self) -> None:
        current_path = self.executable_path()
        start_dir = str(Path(current_path).parent) if current_path else ""
        path, _ = QFileDialog.getOpenFileName(self, "Choose Spine executable", start_dir, "Executable (*.exe);;All files (*)")
        if not path:
            return
        self.path_edit.setText(path)
        self.settings.setValue(self._settings_key(self.selected_version()), path)

    def load_path_for_version(self, version: str) -> None:
        self.path_edit.setText(str(self.settings.value(self._settings_key(version), "")))

    def _settings_key(self, version: str) -> str:
        return f"{self.settings_key_prefix}/spine_{version}"


class ExecutableSelector(QWidget):
    def __init__(self, title: str, settings_key: str, settings: QSettings) -> None:
        super().__init__()
        self.settings_key = settings_key
        self.settings = settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("SectionTitle")
        layout.addWidget(label)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No executable selected")
        path_row.addWidget(self.path_edit, stretch=1)
        self.browse_button = QPushButton("Choose exe")
        self.browse_button.clicked.connect(self.choose_executable)
        path_row.addWidget(self.browse_button)
        layout.addLayout(path_row)

        self.path_edit.setText(str(self.settings.value(self.settings_key, "")))

    def executable_path(self) -> str:
        return self.path_edit.text().strip()

    def choose_executable(self) -> None:
        current_path = self.executable_path()
        start_dir = str(Path(current_path).parent) if current_path else ""
        path, _ = QFileDialog.getOpenFileName(self, "Choose Spine executable", start_dir, "Executable (*.exe);;All files (*)")
        if not path:
            return
        self.path_edit.setText(path)
        self.settings.setValue(self.settings_key, path)


class SpineTargetVersionSelector(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("SectionTitle")
        layout.addWidget(label)

        self.version_combo = QComboBox()
        self.version_combo.addItems(SPINE_VERSIONS)
        self.version_combo.setFixedWidth(140)
        layout.addWidget(self.version_combo)

    def selected_version(self) -> str:
        return self.version_combo.currentText()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Spine Upgrade Pipeline TUN")
        self.resize(1080, 560)
        self.worker_thread: QThread | None = None
        self.worker: PipelineWorker | None = None
        self.settings = QSettings("SpineUpgradePipelineTUN", "SpineUpgradePipelineTUN")

        self.input_type_combo = QComboBox()
        self.input_type_combo.addItems(("Folder", "Archive (.zip/.rar)"))
        self.input_edit = QLineEdit()
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Auto: <input folder or extracted zip>\\SpineNewVersion")
        self.spine_exe_selector = ExecutableSelector("Spine Executable", "spine/executable", self.settings)
        self.new_spine_selector = SpineTargetVersionSelector("Target Version")
        self.input_type_combo.currentTextChanged.connect(self.input_type_changed)
        self.input_edit.textChanged.connect(self.update_output_from_input)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()

        self.run_button = QPushButton("Run Upgrade")
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.clicked.connect(self.start_pipeline)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Spine Upgrade Pipeline TUN")
        title.setObjectName("Title")
        layout.addWidget(title)

        subtitle = QLabel("Upgrade exported Spine runtime assets without changing the original files.")
        subtitle.setObjectName("Muted")
        layout.addWidget(subtitle)

        warning = QLabel(
            "Warning: importing exported skeleton data may not perfectly reconstruct the "
            "original .spine project when nonessential or editor data is missing."
        )
        warning.setObjectName("Warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        paths_card, paths_layout = self._card("Folders")
        paths_layout.addWidget(self._input_row())
        paths_layout.addWidget(self._path_row("Output folder", self.output_edit, None))
        layout.addWidget(paths_card)

        spine_card, spine_layout = self._card("Spine")
        version_row = QHBoxLayout()
        version_row.setSpacing(16)
        version_row.addWidget(self.spine_exe_selector)
        version_row.addWidget(self.new_spine_selector)
        spine_layout.addLayout(version_row)
        layout.addWidget(spine_card)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addWidget(self.run_button)
        actions.addWidget(self.progress)
        actions.addStretch(1)
        layout.addLayout(actions)

        layout.addStretch(1)
        self.setCentralWidget(root)

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)
        label = QLabel(title)
        label.setObjectName("SectionTitle")
        layout.addWidget(label)
        return card, layout

    def _path_row(self, label_text: str, edit: QLineEdit, handler) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        label = QLabel(label_text)
        label.setMinimumWidth(105)
        layout.addWidget(label)
        layout.addWidget(edit, stretch=1)
        if handler is not None:
            button = QPushButton("Choose")
            button.clicked.connect(handler)
            layout.addWidget(button)
        return widget

    def _input_row(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        label = QLabel("Input")
        label.setMinimumWidth(105)
        layout.addWidget(label)
        self.input_type_combo.setFixedWidth(150)
        layout.addWidget(self.input_type_combo)
        layout.addWidget(self.input_edit, stretch=1)
        button = QPushButton("Choose")
        button.clicked.connect(self.choose_input_path)
        layout.addWidget(button)
        return widget

    def input_type_changed(self) -> None:
        self.input_edit.clear()
        self.output_edit.clear()

    def choose_input_path(self) -> None:
        if self.is_archive_input():
            start_dir = str(Path(self.input_edit.text()).parent) if self.input_edit.text().strip() else ""
            path, _ = QFileDialog.getOpenFileName(self, "Choose input archive", start_dir, "Archives (*.zip *.rar)")
        else:
            path = QFileDialog.getExistingDirectory(self, "Choose input folder")
        if path:
            self.input_edit.setText(path)
            self.update_output_from_input()

    def update_output_from_input(self) -> None:
        input_text = self.input_edit.text().strip()
        if not input_text:
            self.output_edit.clear()
        elif self.is_archive_input():
            self.output_edit.setText(str(Path(input_text).with_suffix("") / "SpineNewVersion"))
        else:
            self.output_edit.setText(str(Path(input_text) / "SpineNewVersion"))

    def is_archive_input(self) -> bool:
        return self.input_type_combo.currentText().startswith("Archive")

    def start_pipeline(self) -> None:
        required_fields = [
            ("Spine executable", self.spine_exe_selector.executable_path()),
        ]
        if not self.input_edit.text().strip():
            required_fields.insert(0, ("Input path", ""))
        missing = [label for label, value in required_fields if not value]
        if missing:
            QMessageBox.warning(self, "Cannot run", "Missing required fields:\n" + "\n".join(missing))
            return
        input_path = Path(self.input_edit.text().strip())
        if self.is_archive_input() and input_path.suffix.lower() not in {".zip", ".rar"}:
            QMessageBox.warning(self, "Cannot run", "Archive input must be a .zip or .rar file.")
            return
        if not self.is_archive_input() and input_path.suffix.lower() in {".zip", ".rar"}:
            QMessageBox.warning(self, "Cannot run", "Switch input type to Archive before choosing a .zip or .rar file.")
            return

        archive_path = input_path if self.is_archive_input() else None
        folder_path = Path(".") if self.is_archive_input() else input_path
        config = PipelineConfig(
            input_dir=folder_path,
            output_dir=Path(self.output_edit.text().strip()),
            old_spine_exe=Path(self.spine_exe_selector.executable_path()),
            new_spine_exe=Path(self.spine_exe_selector.executable_path()),
            old_spine_version="",
            new_spine_version=self.new_spine_selector.selected_version(),
            input_archive=archive_path,
        )
        errors = config.validate()
        if errors:
            QMessageBox.warning(self, "Cannot run", "\n".join(errors))
            return

        self.run_button.setEnabled(False)
        self.progress.show()

        self.worker_thread = QThread(self)
        self.worker = PipelineWorker(config)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.pipeline_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    @Slot(str)
    def append_log(self, message: str) -> None:
        _ = message

    @Slot(bool, str)
    def pipeline_finished(self, ok: bool, message: str) -> None:
        self.progress.hide()
        self.run_button.setEnabled(True)
        QMessageBox.information(self, "Pipeline finished" if ok else "Pipeline finished with errors", message)
        self.worker_thread = None
        self.worker = None


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        frame = window.frameGeometry()
        frame.moveCenter(available.center())
        window.move(frame.topLeft())
    window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
    window.show()
    window.raise_()
    window.activateWindow()
    QTimer.singleShot(300, window.raise_)
    QTimer.singleShot(300, window.activateWindow)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
