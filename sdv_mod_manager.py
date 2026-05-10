#!/usr/bin/env python3
"""
OD's Stardew Mod Manager — v1.0
Cross-platform SMAPI mod manager for Stardew Valley.
Supports Linux, macOS, and Windows.
"""

import sys
import os
import json
import shutil
import subprocess
import math
import platform
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QFrame, QScrollArea, QLineEdit,
    QMessageBox, QFileDialog, QStatusBar, QGroupBox,
    QDialog, QDialogButtonBox, QInputDialog, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QPoint
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter, QPainterPath,
    QBrush, QPen, QRadialGradient
)


# ─── Platform Detection ───────────────────────────────────────────────────────

PLATFORM = platform.system()   # "Linux", "Darwin", "Windows"
IS_LINUX   = PLATFORM == "Linux"
IS_MAC     = PLATFORM == "Darwin"
IS_WINDOWS = PLATFORM == "Windows"


# ─── Constants ────────────────────────────────────────────────────────────────

APP_NAME     = "OD's Stardew Mod Manager"
APP_VERSION  = "1.0"
SETTINGS_ORG = "ODsStardewModManager"
SETTINGS_APP = "ODsStardewModManager"
SDV_STEAM_APP_ID = "413150"

# Folder prefix used to disable mods (SMAPI skips dot-prefixed folders on all OS)
DISABLED_PREFIX = "."

# ── Script location — used to find icon.png sitting next to the script/exe ────
# Works whether running as a .py file or a PyInstaller bundle
if getattr(sys, "frozen", False):
    # Running as a PyInstaller executable
    APP_DIR = Path(sys.executable).parent
else:
    # Running as a plain .py script
    APP_DIR = Path(__file__).resolve().parent

ICON_PATH = APP_DIR / "icon.png"

# ── Per-platform config & data paths ─────────────────────────────────────────
if IS_WINDOWS:
    _cfg = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    CONFIG_DIR = _cfg / "ODsStardewModManager"
elif IS_MAC:
    CONFIG_DIR = Path.home() / "Library/Application Support/ODsStardewModManager"
else:  # Linux
    CONFIG_DIR = Path.home() / ".config" / "ODsStardewModManager"

PROFILES_FILE = CONFIG_DIR / "profiles.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# ── Default Mods folder locations ─────────────────────────────────────────────
if IS_WINDOWS:
    _pf   = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
    _pf64 = Path(os.environ.get("ProgramFiles",      "C:/Program Files"))
    DEFAULT_MOD_PATHS = [
        _pf   / "Steam/steamapps/common/Stardew Valley/Mods",
        _pf64 / "Steam/steamapps/common/Stardew Valley/Mods",
        Path.home() / "AppData/Local/Programs/Stardew Valley/Mods",
        Path("C:/GOG Games/Stardew Valley/Mods"),
    ]
    DEFAULT_SMAPI_PATHS = [
        _pf   / "Steam/steamapps/common/Stardew Valley/StardewModdingAPI.exe",
        _pf64 / "Steam/steamapps/common/Stardew Valley/StardewModdingAPI.exe",
    ]
elif IS_MAC:
    DEFAULT_MOD_PATHS = [
        Path.home() / "Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/Mods",
        Path("/Applications/Stardew Valley.app/Contents/MacOS/Mods"),
    ]
    DEFAULT_SMAPI_PATHS = [
        Path.home() / "Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/StardewModdingAPI",
    ]
else:  # Linux
    DEFAULT_MOD_PATHS = [
        Path.home() / "snap/steam/common/.local/share/Steam/steamapps/common/Stardew Valley/Mods",
        Path.home() / ".local/share/Steam/steamapps/common/Stardew Valley/Mods",
        Path.home() / ".steam/steam/steamapps/common/Stardew Valley/Mods",
        Path.home() / "GOG Games/Stardew Valley/Mods",
    ]
    DEFAULT_SMAPI_PATHS = [
        Path.home() / "snap/steam/common/.local/share/Steam/steamapps/common/Stardew Valley/StardewModdingAPI",
        Path.home() / ".local/share/Steam/steamapps/common/Stardew Valley/StardewModdingAPI",
        Path.home() / ".steam/steam/steamapps/common/Stardew Valley/StardewModdingAPI",
    ]


# ─── Colour Palette ───────────────────────────────────────────────────────────

P = {
    "bg":          "#1a1c23",
    "surface":     "#22242e",
    "surface2":    "#2a2d3a",
    "border":      "#353847",
    "accent":      "#7eb87e",
    "accent2":     "#e8c96b",
    "text":        "#e8e8e8",
    "text_dim":    "#8a8fa8",
    "red":         "#e06c6c",
    "green":       "#7eb87e",
    "blue":        "#6c8ee0",
    "disabled_bg": "#181a20",
}


# ─── App Icon ─────────────────────────────────────────────────────────────────

def make_icon() -> QIcon:
    """Load icon.png if present, otherwise draw a fallback icon in code."""
    if ICON_PATH.exists():
        return QIcon(str(ICON_PATH))

    icon = QIcon()
    for size in [16, 32, 48, 64, 128, 256]:
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s, m = size, max(1, size // 16)

        # Background circle
        grad = QRadialGradient(s * 0.5, s * 0.42, s * 0.5)
        grad.setColorAt(0.0, QColor("#2d5a3d"))
        grad.setColorAt(1.0, QColor("#1a3326"))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor("#4a8a5a"), m))
        p.drawEllipse(m, m, s - 2 * m, s - 2 * m)

        # Stem
        sw = max(2, s // 20)
        p.setPen(QPen(QColor("#5a9a4a"), sw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(int(s * 0.50), int(s * 0.58), int(s * 0.50), int(s * 0.82))

        # Leaves
        p.setBrush(QBrush(QColor("#7eb87e")))
        p.setPen(Qt.PenStyle.NoPen)

        def leaf(cx, cy, w, h, angle):
            path = QPainterPath()
            path.moveTo(0, 0)
            path.cubicTo(-w * 0.6, -h * 0.3, -w * 0.4, -h * 0.9, 0, -h)
            path.cubicTo( w * 0.4, -h * 0.9,  w * 0.6, -h * 0.3, 0,  0)
            p.save(); p.translate(cx, cy); p.rotate(angle)
            p.drawPath(path); p.restore()

        lw, lh = s * 0.22, s * 0.28
        leaf(s * 0.50, s * 0.60, lw,        lh,         0)
        leaf(s * 0.50, s * 0.65, lw * 0.85, lh * 0.75,  35)
        leaf(s * 0.50, s * 0.65, lw * 0.85, lh * 0.75, -35)

        # Gold star
        ro, ri = s * 0.18, s * 0.08
        scx, scy = s * 0.50, s * 0.36
        star = QPainterPath()
        for i in range(10):
            r = ro if i % 2 == 0 else ri
            a = math.radians(i * 36 - 90)
            x, y = scx + r * math.cos(a), scy + r * math.sin(a)
            star.moveTo(x, y) if i == 0 else star.lineTo(x, y)
        star.closeSubpath()
        sg = QRadialGradient(scx, scy - ro * 0.3, ro)
        sg.setColorAt(0.0, QColor("#fffbe6"))
        sg.setColorAt(0.5, QColor("#e8c96b"))
        sg.setColorAt(1.0, QColor("#c8922b"))
        p.setBrush(QBrush(sg))
        p.setPen(QPen(QColor("#a06820"), max(1, s // 48)))
        p.drawPath(star)
        p.end()
        icon.addPixmap(px)
    return icon


# ─── Helpers ──────────────────────────────────────────────────────────────────

def read_manifest(mod_path: Path) -> dict:
    manifest = mod_path / "manifest.json"
    if manifest.exists():
        try:
            with open(manifest, encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_mods(mods_dir: Path) -> list[dict]:
    if not mods_dir or not mods_dir.exists():
        return []
    entries = sorted(
        mods_dir / name for name in os.listdir(mods_dir)
        if (mods_dir / name).is_dir()
    )
    mods = []
    for entry in entries:
        disabled    = entry.name.startswith(DISABLED_PREFIX)
        actual_name = entry.name[len(DISABLED_PREFIX):] if disabled else entry.name
        manifest    = read_manifest(entry)
        mods.append({
            "folder":      entry,
            "name":        manifest.get("Name",        actual_name),
            "author":      manifest.get("Author",      "Unknown"),
            "version":     manifest.get("Version",     "?"),
            "desc":        manifest.get("Description", ""),
            "unique_id":   manifest.get("UniqueID",    ""),
            "enabled":     not disabled,
            "folder_name": entry.name,
        })
    return mods


def mod_id(mod: dict) -> str:
    return mod["unique_id"] or mod["folder_name"].lstrip(".")


def find_steam_executable() -> str | None:
    """Locate the Steam binary on any platform."""
    if IS_WINDOWS:
        candidates = [
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Steam/steam.exe",
            Path(os.environ.get("ProgramFiles",      "")) / "Steam/steam.exe",
        ]
    elif IS_MAC:
        candidates = [
            Path("/Applications/Steam.app/Contents/MacOS/steam_osx"),
            Path.home() / "Applications/Steam.app/Contents/MacOS/steam_osx",
        ]
    else:
        candidates = [
            Path("/usr/bin/steam"),
            Path("/usr/local/bin/steam"),
        ]
        found = shutil.which("steam")
        if found:
            candidates.append(Path(found))

    for c in candidates:
        if c and c.exists():
            return str(c)
    return None


def launch_via_steam() -> subprocess.Popen | None:
    """Launch Stardew Valley through Steam using its protocol URL."""
    steam = find_steam_executable()
    if not steam:
        return None
    url = f"steam://rungameid/{SDV_STEAM_APP_ID}"
    if IS_WINDOWS:
        return subprocess.Popen(["cmd", "/c", "start", url], shell=False)
    elif IS_MAC:
        return subprocess.Popen(["open", url])
    else:
        return subprocess.Popen([steam, url])


# ─── Profile Manager ──────────────────────────────────────────────────────────

class ProfileManager:
    """
    Profiles are saved to:
      Linux:   ~/.config/ODsStardewModManager/profiles.json
      macOS:   ~/Library/Application Support/ODsStardewModManager/profiles.json
      Windows: %APPDATA%/ODsStardewModManager/profiles.json

    Each profile stores the list of mod UniqueIDs that should be ENABLED.
    """

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict = {"profiles": {}, "active": None}
        self._load()

    def _load(self):
        if PROFILES_FILE.exists():
            try:
                with open(PROFILES_FILE, encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                pass

    def _save(self):
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def names(self) -> list[str]:
        return list(self._data["profiles"].keys())

    def active(self) -> str | None:
        return self._data.get("active")

    def get(self, name: str) -> list[str]:
        return self._data["profiles"].get(name, [])

    def save_profile(self, name: str, enabled_ids: list[str]):
        self._data["profiles"][name] = enabled_ids
        self._save()

    def delete_profile(self, name: str):
        self._data["profiles"].pop(name, None)
        if self._data.get("active") == name:
            self._data["active"] = None
        self._save()

    def set_active(self, name: str | None):
        self._data["active"] = name
        self._save()

    def rename_profile(self, old: str, new: str):
        if old in self._data["profiles"]:
            self._data["profiles"][new] = self._data["profiles"].pop(old)
            if self._data.get("active") == old:
                self._data["active"] = new
            self._save()


# ─── Launch Thread ────────────────────────────────────────────────────────────

class LaunchThread(QThread):
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, smapi_path: str):
        super().__init__()
        self.smapi_path = smapi_path

    def run(self):
        try:
            proc = launch_via_steam()
            if proc:
                self.finished.emit(f"Launched via Steam (PID {proc.pid})")
                return
            # Fall back to launching SMAPI directly
            result = subprocess.Popen(
                [self.smapi_path],
                cwd=str(Path(self.smapi_path).parent)
            )
            self.finished.emit(f"Launched directly (PID {result.pid})")
        except Exception as e:
            self.error.emit(str(e))


# ─── Mod Card ─────────────────────────────────────────────────────────────────

class ModCard(QWidget):
    toggle_requested = pyqtSignal(dict, bool)

    def __init__(self, mod: dict, parent=None):
        super().__init__(parent)
        self.mod = mod
        self._build()

    def _build(self):
        self.setObjectName("ModCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        self.toggle = QCheckBox()
        self.toggle.setChecked(self.mod["enabled"])
        self.toggle.setFixedSize(22, 22)
        self.toggle.toggled.connect(lambda v: self.toggle_requested.emit(self.mod, v))
        layout.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)

        self.dot = QLabel("●")
        self.dot.setFixedWidth(16)
        self._update_dot()
        layout.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        name_row = QHBoxLayout()
        self.name_label = QLabel(self.mod["name"])
        self.name_label.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        name_row.addWidget(self.name_label)
        name_row.addStretch()
        self.ver_label = QLabel(f"v{self.mod['version']}")
        self.ver_label.setFont(QFont("monospace", 9))
        self.ver_label.setStyleSheet(f"color:{P['text_dim']};")
        name_row.addWidget(self.ver_label)
        text_col.addLayout(name_row)

        self.auth_label = QLabel(f"by {self.mod['author']}")
        self.auth_label.setFont(QFont("monospace", 8))
        self.auth_label.setStyleSheet(f"color:{P['text_dim']};")
        text_col.addWidget(self.auth_label)

        if self.mod["desc"]:
            dl = QLabel(self.mod["desc"])
            dl.setFont(QFont("monospace", 8))
            dl.setStyleSheet(f"color:{P['text_dim']};")
            dl.setWordWrap(True)
            dl.setMaximumHeight(36)
            text_col.addWidget(dl)

        layout.addLayout(text_col, 1)
        self._style()

    def _update_dot(self):
        c = P["green"] if self.mod["enabled"] else P["red"]
        self.dot.setStyleSheet(f"color:{c}; font-size:10px;")

    def _style(self):
        en  = self.mod["enabled"]
        bg  = P["surface2"]   if en else P["disabled_bg"]
        brd = P["accent"]     if en else P["border"]
        self.setStyleSheet(f"""
            #ModCard {{ background:{bg}; border:1px solid {brd}; border-radius:6px; }}
            QCheckBox::indicator {{
                width:18px; height:18px;
                border:2px solid {P['border']}; border-radius:4px; background:{P['surface']};
            }}
            QCheckBox::indicator:checked {{
                background:{P['accent']}; border-color:{P['accent']};
            }}
        """)

    def refresh(self, mod: dict):
        self.mod = mod
        self.toggle.blockSignals(True)
        self.toggle.setChecked(mod["enabled"])
        self.toggle.blockSignals(False)
        self.name_label.setText(mod["name"])
        self.ver_label.setText(f"v{mod['version']}")
        self.auth_label.setText(f"by {mod['author']}")
        self._update_dot()
        self._style()


# ─── Profiles Panel ───────────────────────────────────────────────────────────

class ProfilesPanel(QWidget):
    profile_applied = pyqtSignal(str)  # name, or "__save__:name"

    def __init__(self, profiles: ProfileManager, parent=None):
        super().__init__(parent)
        self.profiles = profiles
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)

        hdr = QHBoxLayout()
        lbl = QLabel("Profiles")
        lbl.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color:{P['accent2']};")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self.btn_new = self._sbtn("＋ New", P["green"])
        self.btn_new.clicked.connect(self._new_profile)
        hdr.addWidget(self.btn_new)
        vl.addLayout(hdr)

        self.list_area = QVBoxLayout()
        self.list_area.setSpacing(4)
        vl.addLayout(self.list_area)
        vl.addStretch()

        self._rebuild()

    def _sbtn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(26)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{color};
                border:1px solid {P['border']}; border-radius:4px;
                padding:0 8px; font-size:10px;
            }}
            QPushButton:hover {{ border-color:{color}; }}
        """)
        return btn

    def _rebuild(self):
        while self.list_area.count():
            item = self.list_area.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active = self.profiles.active()
        if not self.profiles.names():
            empty = QLabel("No profiles yet.\nClick ＋ New to create one.")
            empty.setFont(QFont("monospace", 8))
            empty.setStyleSheet(f"color:{P['text_dim']};")
            empty.setWordWrap(True)
            self.list_area.addWidget(empty)
            return

        for name in self.profiles.names():
            is_active = (name == active)
            row = QWidget()
            row.setObjectName("ProfileRow")
            row.setStyleSheet(f"""
                #ProfileRow {{
                    background:{"#1e3a2a" if is_active else P['surface']};
                    border:1px solid {P['accent'] if is_active else P['border']};
                    border-radius:5px;
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 5, 8, 5)
            rl.setSpacing(6)

            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setStyleSheet(f"color:{P['accent'] if is_active else P['border']}; font-size:9px;")
            rl.addWidget(dot)

            nm_lbl = QLabel(name)
            nm_lbl.setFont(QFont("monospace", 9,
                QFont.Weight.Bold if is_active else QFont.Weight.Normal))
            nm_lbl.setStyleSheet(f"color:{P['accent'] if is_active else P['text']};")
            rl.addWidget(nm_lbl, 1)

            apply_btn = self._sbtn("Apply", P["accent"])
            apply_btn.setToolTip(f"Switch to profile '{name}'")
            apply_btn.clicked.connect(lambda _, n=name: self._apply(n))
            rl.addWidget(apply_btn)

            more_btn = self._sbtn("⋮", P["text_dim"])
            more_btn.setFixedWidth(28)
            more_btn.clicked.connect(lambda _, n=name, b=more_btn: self._menu(n, b))
            rl.addWidget(more_btn)

            self.list_area.addWidget(row)

    def _apply(self, name: str):
        self.profiles.set_active(name)
        self.profile_applied.emit(name)
        self._rebuild()

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.profiles.names():
                QMessageBox.warning(self, "Duplicate",
                    f"A profile named '{name}' already exists.")
                return
            self.profile_applied.emit(f"__save__:{name}")
            self._rebuild()

    def _menu(self, name: str, btn: QPushButton):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background:{P['surface2']}; color:{P['text']};
                border:1px solid {P['border']}; border-radius:4px; padding:4px;
            }}
            QMenu::item {{ padding:4px 16px; border-radius:3px; }}
            QMenu::item:selected {{ background:{P['surface']}; color:{P['accent']}; }}
        """)
        rename_act    = menu.addAction("✏  Rename")
        overwrite_act = menu.addAction("💾  Overwrite with current mods")
        menu.addSeparator()
        delete_act = menu.addAction("🗑  Delete")

        action = menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))

        if action == rename_act:
            new_name, ok = QInputDialog.getText(
                self, "Rename Profile", "New name:", text=name)
            if ok and new_name.strip() and new_name.strip() != name:
                self.profiles.rename_profile(name, new_name.strip())
                self._rebuild()
        elif action == overwrite_act:
            self.profile_applied.emit(f"__save__:{name}")
        elif action == delete_act:
            if QMessageBox.question(self, "Delete Profile",
                    f"Delete profile '{name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes:
                self.profiles.delete_profile(name)
                self._rebuild()

    def refresh(self):
        self._rebuild()



# ─── First Launch Setup Dialog ────────────────────────────────────────────────

class FirstLaunchDialog(QDialog):
    """
    Shown on first launch (when no paths are saved in settings).
    Guides the user to set their Mods directory and SMAPI executable.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mods_dir   = ""
        self.smapi_path = ""
        self._build()

    def _build(self):
        self.setWindowTitle(f"Welcome to {APP_NAME}")
        self.setWindowIcon(make_icon())
        self.setMinimumWidth(580)
        self.setModal(True)

        vl = QVBoxLayout(self)
        vl.setSpacing(16)
        vl.setContentsMargins(24, 24, 24, 24)

        # Header
        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon().pixmap(48, 48))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(icon_lbl)

        title = QLabel(f"Welcome to {APP_NAME}!")
        title.setFont(QFont("monospace", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color:{P['accent']};")
        vl.addWidget(title)

        subtitle = QLabel(
            "Before you get started, please tell the app where your\n"
            "Stardew Valley Mods folder and SMAPI executable are located."
        )
        subtitle.setFont(QFont("monospace", 9))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color:{P['text_dim']};")
        vl.addWidget(subtitle)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color:{P['border']};")
        vl.addWidget(line)

        field_style = (
            f"background:{P['surface2']}; border:1px solid {P['border']};"
            f"border-radius:4px; color:{P['text']}; padding:4px 8px; font-size:11px;"
        )
        btn_style = (
            f"QPushButton {{ background:{P['surface2']}; color:{P['text']};"
            f"border:1px solid {P['border']}; border-radius:4px; padding:4px 14px; font-size:11px; }}"
            f"QPushButton:hover {{ border-color:{P['accent']}; color:{P['accent']}; }}"
        )

        # Mods directory
        mods_lbl = QLabel("📁  Mods Directory")
        mods_lbl.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        mods_lbl.setStyleSheet(f"color:{P['accent2']};")
        vl.addWidget(mods_lbl)

        mods_hint = QLabel(
            "The \'Mods\' folder inside your Stardew Valley installation.\n"
            "SMAPI tells you this path in its log: [SMAPI] Mods go here: ..."
        )
        mods_hint.setFont(QFont("monospace", 8))
        mods_hint.setStyleSheet(f"color:{P['text_dim']};")
        vl.addWidget(mods_hint)

        mods_row = QHBoxLayout()
        self.mods_edit = QLineEdit()
        self.mods_edit.setPlaceholderText("Click Browse to select your Mods folder…")
        self.mods_edit.setStyleSheet(field_style)
        self.mods_edit.textChanged.connect(self._validate)
        mods_row.addWidget(self.mods_edit, 1)
        mods_btn = QPushButton("Browse…")
        mods_btn.setStyleSheet(btn_style)
        mods_btn.clicked.connect(self._browse_mods)
        mods_row.addWidget(mods_btn)
        vl.addLayout(mods_row)

        self.mods_status = QLabel("")
        self.mods_status.setFont(QFont("monospace", 8))
        vl.addWidget(self.mods_status)

        # SMAPI executable
        smapi_lbl = QLabel("⚙️  SMAPI Executable")
        smapi_lbl.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        smapi_lbl.setStyleSheet(f"color:{P['accent2']};")
        vl.addWidget(smapi_lbl)

        smapi_hint = QLabel(
            "The StardewModdingAPI file inside your Stardew Valley folder.\n"
            "On Windows this is StardewModdingAPI.exe"
        )
        smapi_hint.setFont(QFont("monospace", 8))
        smapi_hint.setStyleSheet(f"color:{P['text_dim']};")
        vl.addWidget(smapi_hint)

        smapi_row = QHBoxLayout()
        self.smapi_edit = QLineEdit()
        self.smapi_edit.setPlaceholderText("Click Browse to select StardewModdingAPI…")
        self.smapi_edit.setStyleSheet(field_style)
        self.smapi_edit.textChanged.connect(self._validate)
        smapi_row.addWidget(self.smapi_edit, 1)
        smapi_btn = QPushButton("Browse…")
        smapi_btn.setStyleSheet(btn_style)
        smapi_btn.clicked.connect(self._browse_smapi)
        smapi_row.addWidget(smapi_btn)
        vl.addLayout(smapi_row)

        self.smapi_status = QLabel("")
        self.smapi_status.setFont(QFont("monospace", 8))
        vl.addWidget(self.smapi_status)

        # Buttons
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"color:{P['border']};")
        vl.addWidget(line2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.skip_btn = QPushButton("Skip for now")
        self.skip_btn.setFixedHeight(34)
        self.skip_btn.setStyleSheet(
            f"QPushButton {{ background:{P['surface2']}; color:{P['text_dim']};"
            f"border:1px solid {P['border']}; border-radius:5px; padding:0 16px; }}"
            f"QPushButton:hover {{ border-color:{P['border']}; color:{P['text']}; }}"
        )
        self.skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.skip_btn)

        self.ok_btn = QPushButton("✓  Let\'s Go!")
        self.ok_btn.setFixedHeight(34)
        self.ok_btn.setEnabled(False)
        self.ok_btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['accent']}; color:#1a1c23; border:none;
                border-radius:5px; padding:0 24px; font-size:12px; font-weight:bold;
            }}
            QPushButton:hover    {{ background:#96c896; }}
            QPushButton:disabled {{ background:{P['border']}; color:{P['text_dim']}; }}
        """)
        self.ok_btn.clicked.connect(self._accept)
        btn_row.addWidget(self.ok_btn)
        vl.addLayout(btn_row)

        self.setStyleSheet(f"""
            QDialog {{ background:{P['bg']}; color:{P['text']}; font-family:monospace; }}
            QLabel  {{ color:{P['text']}; }}
        """)

    def _browse_mods(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select your Mods folder", str(Path.home()))
        if path:
            self.mods_edit.setText(path)

    def _browse_smapi(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select StardewModdingAPI executable", str(Path.home()))
        if path:
            self.smapi_edit.setText(path)

    def _validate(self):
        mods_ok  = bool(self.mods_edit.text().strip()  and Path(self.mods_edit.text().strip()).exists())
        smapi_ok = bool(self.smapi_edit.text().strip() and Path(self.smapi_edit.text().strip()).exists())

        if self.mods_edit.text().strip():
            if mods_ok:
                self.mods_status.setText("✓  Found!")
                self.mods_status.setStyleSheet(f"color:{P['green']};")
            else:
                self.mods_status.setText("✗  Path not found")
                self.mods_status.setStyleSheet(f"color:{P['red']};")
        else:
            self.mods_status.setText("")

        if self.smapi_edit.text().strip():
            if smapi_ok:
                self.smapi_status.setText("✓  Found!")
                self.smapi_status.setStyleSheet(f"color:{P['green']};")
            else:
                self.smapi_status.setText("✗  Path not found")
                self.smapi_status.setStyleSheet(f"color:{P['red']};")
        else:
            self.smapi_status.setText("")

        self.ok_btn.setEnabled(mods_ok and smapi_ok)

    def _accept(self):
        self.mods_dir   = self.mods_edit.text().strip()
        self.smapi_path = self.smapi_edit.text().strip()
        self.accept()


# ─── Main Window ──────────────────────────────────────────────────────────────

class SDVModManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings   = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.profiles   = ProfileManager()
        self.mods_dir:  Path | None = None
        self.smapi_path: str = ""
        self.mods:      list[dict] = []
        self.mod_cards: list[ModCard] = []
        self._load_settings()
        self._build_ui()
        self._apply_theme()
        self.refresh_mods()
        # Show first-launch setup dialog if neither path was found
        if not self.mods_dir and not self.smapi_path:
            self._show_first_launch()

    # ── Settings ──────────────────────────────────────────────────────────────

    def _load_settings(self):
        saved_mods  = self.settings.value("mods_dir",   "")
        saved_smapi = self.settings.value("smapi_path", "")

        if saved_mods and Path(saved_mods).exists():
            self.mods_dir = Path(saved_mods)
        else:
            for p in DEFAULT_MOD_PATHS:
                if p.exists():
                    self.mods_dir = p
                    break

        if saved_smapi and Path(saved_smapi).exists():
            self.smapi_path = saved_smapi
        else:
            for p in DEFAULT_SMAPI_PATHS:
                if p.exists():
                    self.smapi_path = str(p)
                    break

    def _save_settings(self):
        if self.mods_dir:
            self.settings.setValue("mods_dir", str(self.mods_dir))
        self.settings.setValue("smapi_path", self.smapi_path)

    def _show_first_launch(self):
        dlg = FirstLaunchDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.mods_dir and Path(dlg.mods_dir).exists():
                self.mods_dir = Path(dlg.mods_dir)
            if dlg.smapi_path and Path(dlg.smapi_path).exists():
                self.smapi_path = dlg.smapi_path
            self._save_settings()
            self.refresh_mods()
            self._update_path_labels()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowIcon(make_icon())
        self.setMinimumSize(900, 640)
        self.resize(
            int(self.settings.value("width",  1020)),
            int(self.settings.value("height",  700))
        )

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_content(), 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.setStyleSheet(f"""
            QStatusBar {{
                background:{P['bg']}; color:{P['text_dim']};
                font-size:11px; border-top:1px solid {P['border']}; padding:2px 8px;
            }}
        """)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        header.setFixedHeight(64)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon().pixmap(40, 40))
        hl.addWidget(icon_lbl)
        hl.addSpacing(8)

        title = QLabel(APP_NAME)
        title.setFont(QFont("monospace", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{P['accent']}; letter-spacing:1px;")
        hl.addWidget(title)

        sub = QLabel(f"v{APP_VERSION}")
        sub.setFont(QFont("monospace", 9))
        sub.setStyleSheet(f"color:{P['text_dim']};")
        sub.setAlignment(Qt.AlignmentFlag.AlignBottom)
        hl.addWidget(sub)
        hl.addStretch()

        # Platform badge
        plat_lbl = QLabel(PLATFORM)
        plat_lbl.setFont(QFont("monospace", 9))
        plat_lbl.setStyleSheet(f"""
            color:{P['blue']}; background:{P['surface2']};
            border:1px solid {P['border']}; border-radius:8px; padding:2px 8px;
        """)
        hl.addWidget(plat_lbl)
        hl.addSpacing(6)

        self.count_label = QLabel("0 mods")
        self.count_label.setFont(QFont("monospace", 10))
        self.count_label.setStyleSheet(f"""
            color:{P['text_dim']}; background:{P['surface2']};
            border:1px solid {P['border']}; border-radius:10px; padding:2px 10px;
        """)
        hl.addWidget(self.count_label)
        return header

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("Toolbar")
        bar.setFixedHeight(52)
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(16, 6, 16, 6)
        hl.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search mods…")
        self.search.setFixedWidth(220)
        self.search.textChanged.connect(self._filter_mods)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background:{P['surface2']}; border:1px solid {P['border']};
                border-radius:6px; color:{P['text']}; padding:4px 10px; font-size:11px;
            }}
            QLineEdit:focus {{ border-color:{P['accent']}; }}
        """)
        hl.addWidget(self.search)
        hl.addStretch()

        self.btn_enable_all = self._tbtn("Enable All",  P["green"])
        self.btn_enable_all.clicked.connect(self._enable_all)
        hl.addWidget(self.btn_enable_all)

        self.btn_disable_all = self._tbtn("Disable All", P["red"])
        self.btn_disable_all.clicked.connect(self._disable_all)
        hl.addWidget(self.btn_disable_all)

        hl.addWidget(self._sep())

        self.btn_paths = self._tbtn("⚙  Paths", P["text_dim"])
        self.btn_paths.clicked.connect(self._show_paths_dialog)
        hl.addWidget(self.btn_paths)

        self.btn_refresh = self._tbtn("↺  Refresh", P["blue"])
        self.btn_refresh.clicked.connect(self.refresh_mods)
        hl.addWidget(self.btn_refresh)

        hl.addWidget(self._sep())

        self.btn_launch = QPushButton("▶  Launch with SMAPI")
        self.btn_launch.setFixedHeight(36)
        self.btn_launch.clicked.connect(self._launch_smapi)
        self.btn_launch.setStyleSheet(f"""
            QPushButton {{
                background:{P['accent']}; color:#1a1c23; border:none;
                border-radius:6px; padding:0 18px; font-size:12px; font-weight:bold;
            }}
            QPushButton:hover   {{ background:#96c896; }}
            QPushButton:pressed {{ background:#5a9a5a; }}
            QPushButton:disabled {{ background:{P['border']}; color:{P['text_dim']}; }}
        """)
        hl.addWidget(self.btn_launch)
        return bar

    def _tbtn(self, text: str, color: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{color};
                border:1px solid {P['border']}; border-radius:5px;
                padding:0 12px; font-size:11px;
            }}
            QPushButton:hover   {{ background:{P['surface']}; border-color:{color}; }}
            QPushButton:pressed {{ background:{P['bg']}; }}
        """)
        return btn

    def _sep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{P['border']};")
        return sep

    def _build_content(self) -> QWidget:
        container = QWidget()
        hl = QHBoxLayout(container)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(10)

        # ── Mod list panel ────────────────────────────────────────────────────
        list_panel = QWidget()
        vl = QVBoxLayout(list_panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)

        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("monospace", 9))
        self.stats_label.setStyleSheet(f"color:{P['text_dim']}; padding-left:4px;")
        vl.addWidget(self.stats_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background:transparent; border:none; }}
            QScrollBar:vertical {{
                background:{P['surface']}; width:8px; border-radius:4px;
            }}
            QScrollBar::handle:vertical {{
                background:{P['border']}; border-radius:4px; min-height:24px;
            }}
            QScrollBar::handle:vertical:hover {{ background:{P['accent']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background:transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(5)
        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_container)
        vl.addWidget(scroll, 1)
        hl.addWidget(list_panel, 1)

        # ── Side panel ────────────────────────────────────────────────────────
        side = QWidget()
        side.setFixedWidth(230)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(6, 0, 0, 0)
        sl.setSpacing(10)

        # Profiles
        prof_box = QGroupBox("Profiles")
        pb_vl = QVBoxLayout(prof_box)
        pb_vl.setContentsMargins(8, 8, 8, 8)
        pb_vl.setSpacing(6)

        self.profiles_panel = ProfilesPanel(self.profiles)
        self.profiles_panel.profile_applied.connect(self._on_profile_signal)
        pb_vl.addWidget(self.profiles_panel)

        save_btn = QPushButton("💾  Save current as profile")
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{P['accent2']};
                border:1px solid {P['border']}; border-radius:4px;
                padding:0 8px; font-size:10px;
            }}
            QPushButton:hover {{ border-color:{P['accent2']}; }}
        """)
        save_btn.clicked.connect(self._save_current_as_profile)
        pb_vl.addWidget(save_btn)
        sl.addWidget(prof_box)

        # Paths info
        paths_box = QGroupBox("Paths")
        paths_vl = QVBoxLayout(paths_box)
        self.mods_path_label = QLabel("Mods dir:\n—")
        self.mods_path_label.setFont(QFont("monospace", 8))
        self.mods_path_label.setStyleSheet(f"color:{P['text_dim']};")
        self.mods_path_label.setWordWrap(True)
        paths_vl.addWidget(self.mods_path_label)
        self.smapi_path_label = QLabel("SMAPI:\n—")
        self.smapi_path_label.setFont(QFont("monospace", 8))
        self.smapi_path_label.setStyleSheet(f"color:{P['text_dim']};")
        self.smapi_path_label.setWordWrap(True)
        paths_vl.addWidget(self.smapi_path_label)
        sl.addWidget(paths_box)

        # Legend
        legend_box = QGroupBox("Legend")
        leg_vl = QVBoxLayout(legend_box)
        for sym, lbl, col in [("●", "Enabled", P["green"]), ("●", "Disabled", P["red"])]:
            row = QHBoxLayout()
            d = QLabel(sym)
            d.setFixedWidth(16)
            d.setStyleSheet(f"color:{col}; font-size:10px;")
            row.addWidget(d)
            t = QLabel(lbl)
            t.setFont(QFont("monospace", 9))
            t.setStyleSheet(f"color:{P['text_dim']};")
            row.addWidget(t)
            row.addStretch()
            leg_vl.addLayout(row)
        sl.addWidget(legend_box)

        sl.addStretch()
        hl.addWidget(side)
        return container

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background:{P['bg']}; color:{P['text']}; font-family:monospace;
            }}
            #Header  {{ background:{P['surface']}; border-bottom:1px solid {P['border']}; }}
            #Toolbar {{ background:{P['surface']}; border-bottom:1px solid {P['border']}; }}
            QGroupBox {{
                background:{P['surface']}; border:1px solid {P['border']};
                border-radius:6px; margin-top:12px; padding:6px;
                font-size:10px; color:{P['accent2']};
            }}
            QGroupBox::title {{
                subcontrol-origin:margin; subcontrol-position:top left;
                padding:0 6px; color:{P['accent2']}; font-size:10px;
            }}
        """)

    # ── Mod Logic ─────────────────────────────────────────────────────────────

    def refresh_mods(self):
        self.mods = get_mods(self.mods_dir) if self.mods_dir else []
        self._rebuild_cards()
        self._update_path_labels()
        self._update_stats()
        n = len(self.mods)
        self.status.showMessage(
            f"Loaded {n} mod{'s' if n != 1 else ''} "
            f"from {self.mods_dir or '(no path set)'}"
        )

    def _rebuild_cards(self):
        for card in self.mod_cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.mod_cards.clear()

        if self.cards_layout.count():
            self.cards_layout.takeAt(self.cards_layout.count() - 1)

        query = self.search.text().lower()
        for mod in self.mods:
            if query and query not in mod["name"].lower() \
                     and query not in mod["author"].lower():
                continue
            card = ModCard(mod)
            card.toggle_requested.connect(self._on_toggle)
            self.cards_layout.addWidget(card)
            self.mod_cards.append(card)

        self.cards_layout.addStretch()
        self._update_stats()

    def _filter_mods(self):
        self._rebuild_cards()

    def _on_toggle(self, mod: dict, enable: bool):
        folder: Path = mod["folder"]
        try:
            if enable:
                new_name = (folder.name[len(DISABLED_PREFIX):]
                            if folder.name.startswith(DISABLED_PREFIX)
                            else folder.name)
            else:
                new_name = (folder.name
                            if folder.name.startswith(DISABLED_PREFIX)
                            else DISABLED_PREFIX + folder.name)

            new_path = folder.parent / new_name
            if new_path != folder:
                folder.rename(new_path)
            mod["folder"]      = new_path
            mod["folder_name"] = new_name
            mod["enabled"]     = enable

            for card in self.mod_cards:
                if card.mod is mod:
                    card.refresh(mod)

            self.status.showMessage(
                f"{'Enabled' if enable else 'Disabled'}: {mod['name']}"
            )
            self._update_stats()
        except PermissionError:
            QMessageBox.critical(self, "Permission Error",
                f"Cannot rename:\n{folder}\n\nCheck file permissions.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _enable_all(self):
        for mod in self.mods:
            if not mod["enabled"]:
                self._on_toggle(mod, True)
        for card in self.mod_cards:
            card.refresh(card.mod)

    def _disable_all(self):
        for mod in self.mods:
            if mod["enabled"]:
                self._on_toggle(mod, False)
        for card in self.mod_cards:
            card.refresh(card.mod)

    def _update_stats(self):
        total    = len(self.mods)
        enabled  = sum(1 for m in self.mods if m["enabled"])
        disabled = total - enabled
        green, red = P["green"], P["red"]
        self.count_label.setText(f"{total} mods")
        self.stats_label.setText(
            f"<span style='color:{green}'>{enabled} enabled</span>"
            "  ·  "
            f"<span style='color:{red}'>{disabled} disabled</span>"
        )

    def _update_path_labels(self):
        self.mods_path_label.setText(
            f"Mods dir:\n{self.mods_dir or 'Not set'}")
        self.smapi_path_label.setText(
            f"SMAPI:\n{self.smapi_path or 'Not set'}")
        ok = bool(self.smapi_path and Path(self.smapi_path).exists())
        self.btn_launch.setEnabled(ok)

    # ── Profiles Logic ────────────────────────────────────────────────────────

    def _current_enabled_ids(self) -> list[str]:
        return [mod_id(m) for m in self.mods if m["enabled"]]

    def _save_current_as_profile(self):
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.profiles.names():
            if QMessageBox.question(
                self, "Overwrite?",
                f"Profile '{name}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
        self.profiles.save_profile(name, self._current_enabled_ids())
        self.profiles.set_active(name)
        self.profiles_panel.refresh()
        self.status.showMessage(f"Saved profile: {name}")

    def _on_profile_signal(self, signal: str):
        if signal.startswith("__save__:"):
            name = signal[len("__save__:"):]
            self.profiles.save_profile(name, self._current_enabled_ids())
            self.profiles.set_active(name)
            self.profiles_panel.refresh()
            self.status.showMessage(f"Saved profile: {name}")
        else:
            # Apply profile: enable mods in list, disable everything else
            profile_ids = set(self.profiles.get(signal))
            for mod in self.mods:
                want = mod_id(mod) in profile_ids
                if mod["enabled"] != want:
                    self._on_toggle(mod, want)
            for card in self.mod_cards:
                card.refresh(card.mod)
            self.status.showMessage(f"Applied profile: {signal}")

    # ── Paths Dialog ──────────────────────────────────────────────────────────

    def _show_paths_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Configure Paths")
        dlg.setMinimumWidth(560)
        dlg.setStyleSheet(self.styleSheet())
        vl = QVBoxLayout(dlg)
        vl.setSpacing(12)

        field_style = (
            f"background:{P['surface2']}; border:1px solid {P['border']};"
            f"border-radius:4px; color:{P['text']}; padding:4px 8px;"
        )
        btn_style = (
            f"QPushButton {{ background:{P['surface2']}; color:{P['text']};"
            f"border:1px solid {P['border']}; border-radius:4px; padding:4px 12px; }}"
            f"QPushButton:hover {{ border-color:{P['accent']}; }}"
        )

        vl.addWidget(QLabel("Mods Directory:"))
        mods_row  = QHBoxLayout()
        mods_edit = QLineEdit(str(self.mods_dir) if self.mods_dir else "")
        mods_edit.setStyleSheet(field_style)
        mods_row.addWidget(mods_edit, 1)
        mb = QPushButton("Browse…")
        mb.setStyleSheet(btn_style)
        mb.clicked.connect(lambda: mods_edit.setText(
            QFileDialog.getExistingDirectory(
                dlg, "Select Mods Directory",
                str(self.mods_dir or Path.home())
            ) or mods_edit.text()
        ))
        mods_row.addWidget(mb)
        vl.addLayout(mods_row)

        vl.addWidget(QLabel("SMAPI Executable:"))
        smapi_row  = QHBoxLayout()
        smapi_edit = QLineEdit(self.smapi_path or "")
        smapi_edit.setStyleSheet(field_style)
        smapi_row.addWidget(smapi_edit, 1)
        sb = QPushButton("Browse…")
        sb.setStyleSheet(btn_style)
        sb.clicked.connect(lambda: smapi_edit.setText(
            QFileDialog.getOpenFileName(
                dlg, "Select SMAPI Executable", str(Path.home())
            )[0] or smapi_edit.text()
        ))
        smapi_row.addWidget(sb)
        vl.addLayout(smapi_row)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        bb.setStyleSheet(
            f"QPushButton {{ background:{P['surface2']}; color:{P['text']};"
            f"border:1px solid {P['border']}; border-radius:4px;"
            f"padding:4px 16px; min-width:70px; }}"
            f"QPushButton:hover {{ border-color:{P['accent']}; }}"
        )
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        vl.addWidget(bb)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            changed = False
            nm = mods_edit.text().strip()
            ns = smapi_edit.text().strip()
            if nm and Path(nm).exists():
                self.mods_dir = Path(nm); changed = True
            elif nm:
                QMessageBox.warning(self, "Invalid",
                    f"Mods directory not found:\n{nm}")
            if ns and Path(ns).exists():
                self.smapi_path = ns; changed = True
            elif ns:
                QMessageBox.warning(self, "Invalid",
                    f"SMAPI executable not found:\n{ns}")
            if changed:
                self._save_settings()
                self.refresh_mods()

    # ── Launch ────────────────────────────────────────────────────────────────

    def _launch_smapi(self):
        if not self.smapi_path or not Path(self.smapi_path).exists():
            QMessageBox.warning(self, "SMAPI Not Found",
                "Configure the SMAPI path in ⚙ Paths.")
            return
        self.btn_launch.setEnabled(False)
        self.btn_launch.setText("▶  Launching…")
        self.launch_thread = LaunchThread(self.smapi_path)
        self.launch_thread.finished.connect(self._on_launched)
        self.launch_thread.error.connect(self._on_launch_error)
        self.launch_thread.start()

    def _on_launched(self, msg: str):
        self.status.showMessage(msg)
        self.btn_launch.setText("▶  Launch with SMAPI")
        self.btn_launch.setEnabled(True)

    def _on_launch_error(self, msg: str):
        QMessageBox.critical(self, "Launch Failed",
            f"Could not start SMAPI:\n{msg}")
        self.btn_launch.setText("▶  Launch with SMAPI")
        self.btn_launch.setEnabled(True)

    # ── Window Events ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self.settings.setValue("width",  self.width())
        self.settings.setValue("height", self.height())
        self._save_settings()
        super().closeEvent(event)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(SETTINGS_ORG)
    app.setWindowIcon(make_icon())

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(P["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(P["text"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(P["surface"]))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(P["surface2"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(P["surface2"]))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(P["text"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(P["text"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(P["surface2"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(P["text"]))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(P["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(P["bg"]))
    app.setPalette(pal)

    win = SDVModManager()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
