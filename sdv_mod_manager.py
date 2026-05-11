#!/usr/bin/env python3
"""
OD's Stardew Mod Manager — v3.0
Cross-platform SMAPI mod manager for Stardew Valley.
Supports Linux, macOS, and Windows.

New in v2.0:
  - Mod details panel
  - Sort & filter options
  - Profile import/export
  - Drag to reorder
  - Favourites
  - Mod count per profile
  - Built-in SMAPI log viewer

New in v3.0:
  - ZIP installer (drop .zip mods in Mods folder, click Unzip)
  - Windows Terminal–accurate SMAPI log colours
  - Automatic path detection on first launch
  - Real dependency info from manifest.json only
"""

import sys
import os
import json
import shutil
import subprocess
import math
import platform
import re
import zipfile
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QFrame, QScrollArea, QLineEdit,
    QMessageBox, QFileDialog, QStatusBar, QGroupBox,
    QDialog, QDialogButtonBox, QInputDialog, QMenu, QComboBox,
    QSplitter, QTextEdit, QTabWidget, QAbstractItemView,
    QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSettings, QPoint, QMimeData,
    QByteArray, QTimer
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter, QPainterPath,
    QBrush, QPen, QRadialGradient, QDrag
)


# ─── Platform Detection ───────────────────────────────────────────────────────

PLATFORM   = platform.system()
IS_LINUX   = PLATFORM == "Linux"
IS_MAC     = PLATFORM == "Darwin"
IS_WINDOWS = PLATFORM == "Windows"


# ─── Constants ────────────────────────────────────────────────────────────────

APP_NAME         = "OD's Stardew Mod Manager"
APP_VERSION      = "1.1"
SETTINGS_ORG     = "ODsStardewModManager"
SETTINGS_APP     = "ODsStardewModManager"
SDV_STEAM_APP_ID = "413150"
DISABLED_PREFIX  = "."

# App directory (next to script or executable)
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).resolve().parent

ICON_PATH = APP_DIR / "icon.png"

# Config directory
if IS_WINDOWS:
    _cfg = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    CONFIG_DIR = _cfg / "ODsStardewModManager"
elif IS_MAC:
    CONFIG_DIR = Path.home() / "Library/Application Support/ODsStardewModManager"
else:
    CONFIG_DIR = Path.home() / ".config" / "ODsStardewModManager"

PROFILES_FILE  = CONFIG_DIR / "profiles.json"
FAVOURITES_FILE = CONFIG_DIR / "favourites.json"
ORDER_FILE     = CONFIG_DIR / "order.json"

# Default paths
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
    SMAPI_LOG_PATHS = [
        Path.home() / "AppData/Roaming/StardewValley/ErrorLogs/SMAPI-latest.txt",
    ]
elif IS_MAC:
    DEFAULT_MOD_PATHS = [
        Path.home() / "Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/Mods",
        Path("/Applications/Stardew Valley.app/Contents/MacOS/Mods"),
    ]
    DEFAULT_SMAPI_PATHS = [
        Path.home() / "Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/StardewModdingAPI",
    ]
    SMAPI_LOG_PATHS = [
        Path.home() / ".config/StardewValley/ErrorLogs/SMAPI-latest.txt",
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
    SMAPI_LOG_PATHS = [
        Path.home() / ".config/StardewValley/ErrorLogs/SMAPI-latest.txt",
        Path.home() / "snap/steam/common/.local/share/StardewValley/ErrorLogs/SMAPI-latest.txt",
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
    "orange":      "#e09a6c",
    "disabled_bg": "#181a20",
    "drag_highlight": "#3a4a3a",
}

# Windows Terminal / SMAPI console colours (matches the actual SMAPI output)
LOG_COLOURS = {
    # Level tags — matched by priority (first match wins per line)
    "[ERROR]":   "#c50f1f",   # Bright Red
    "[WARN]":    "#c19c00",   # Dark Yellow / Gold
    "[INFO]":    "#cccccc",   # Light Grey (default terminal text)
    "[DEBUG]":   "#767676",   # Dark Grey
    "[TRACE]":   "#767676",   # Dark Grey (same as DEBUG)
    "[ALL]":     "#767676",   # Dark Grey
    # Source tags — SMAPI module colours
    "[SMAPI]":   "#13a10e",   # Bright Green
    "[game]":    "#3b78ff",   # Bright Blue
    "[Content]": "#16c60c",   # Green
    "[ConsoleCommands]": "#cccccc",
    "[SaveBackup]":      "#cccccc",
}

# Lines that contain these strings get the listed colour regardless of level
LOG_LINE_OVERRIDES = {
    "Exception":          "#c50f1f",
    "System.":            "#c50f1f",
    "SMAPI loaded":       "#13a10e",
    "Loaded":             "#cccccc",
    "Launching mods":     "#13a10e",
    "Mods loaded":        "#13a10e",
}


# ─── Icon ─────────────────────────────────────────────────────────────────────

def make_icon() -> QIcon:
    if ICON_PATH.exists():
        return QIcon(str(ICON_PATH))
    icon = QIcon()
    for size in [16, 32, 48, 64, 128, 256]:
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s, m = size, max(1, size // 16)
        grad = QRadialGradient(s * 0.5, s * 0.42, s * 0.5)
        grad.setColorAt(0.0, QColor("#2d5a3d"))
        grad.setColorAt(1.0, QColor("#1a3326"))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor("#4a8a5a"), m))
        p.drawEllipse(m, m, s - 2*m, s - 2*m)
        sw = max(2, s // 20)
        p.setPen(QPen(QColor("#5a9a4a"), sw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(int(s*.50), int(s*.58), int(s*.50), int(s*.82))
        p.setBrush(QBrush(QColor("#7eb87e")))
        p.setPen(Qt.PenStyle.NoPen)
        def leaf(cx, cy, w, h, angle):
            path = QPainterPath()
            path.moveTo(0,0)
            path.cubicTo(-w*.6,-h*.3,-w*.4,-h*.9,0,-h)
            path.cubicTo(w*.4,-h*.9,w*.6,-h*.3,0,0)
            p.save(); p.translate(cx,cy); p.rotate(angle)
            p.drawPath(path); p.restore()
        lw,lh = s*.22,s*.28
        leaf(s*.50,s*.60,lw,lh,0)
        leaf(s*.50,s*.65,lw*.85,lh*.75,35)
        leaf(s*.50,s*.65,lw*.85,lh*.75,-35)
        ro,ri = s*.18,s*.08
        scx,scy = s*.50,s*.36
        star = QPainterPath()
        for i in range(10):
            r = ro if i%2==0 else ri
            a = math.radians(i*36-90)
            x,y = scx+r*math.cos(a), scy+r*math.sin(a)
            star.moveTo(x,y) if i==0 else star.lineTo(x,y)
        star.closeSubpath()
        sg = QRadialGradient(scx, scy-ro*.3, ro)
        sg.setColorAt(0.0, QColor("#fffbe6"))
        sg.setColorAt(0.5, QColor("#e8c96b"))
        sg.setColorAt(1.0, QColor("#c8922b"))
        p.setBrush(QBrush(sg))
        p.setPen(QPen(QColor("#a06820"), max(1,s//48)))
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

    all_names = os.listdir(mods_dir)
    mods = []

    # ── Installed mod folders ─────────────────────────────────────────────────
    for name in sorted(all_names):
        entry = mods_dir / name
        if not entry.is_dir():
            continue
        disabled    = name.startswith(DISABLED_PREFIX)
        actual_name = name[len(DISABLED_PREFIX):] if disabled else name
        manifest    = read_manifest(entry)

        # Only include deps that actually appear in the manifest; never fabricate
        raw_deps = manifest.get("Dependencies", [])
        deps = [d for d in raw_deps if isinstance(d, dict) and d.get("UniqueID")]

        mods.append({
            "folder":       entry,
            "name":         manifest.get("Name",               actual_name),
            "author":       manifest.get("Author",             "Unknown"),
            "version":      manifest.get("Version",            "?"),
            "desc":         manifest.get("Description",        ""),
            "unique_id":    manifest.get("UniqueID",           ""),
            "min_api":      manifest.get("MinimumApiVersion",  ""),
            "deps":         deps,
            "enabled":      not disabled,
            "folder_name":  name,
            "has_manifest": (entry / "manifest.json").exists(),
            "is_zip":       False,
            "zip_path":     None,
        })

    # ── ZIP files waiting to be installed ────────────────────────────────────
    for name in sorted(all_names):
        entry = mods_dir / name
        if entry.is_file() and name.lower().endswith(".zip"):
            # Peek inside the zip to try to find a manifest
            zip_name = manifest_name = name[:-4]  # strip .zip
            zip_author  = "Unknown"
            zip_version = "?"
            zip_desc    = ""
            try:
                with zipfile.ZipFile(entry) as zf:
                    for zname in zf.namelist():
                        if zname.endswith("manifest.json"):
                            with zf.open(zname) as mf:
                                mdata = json.load(mf)
                                manifest_name = mdata.get("Name",        zip_name)
                                zip_author    = mdata.get("Author",      "Unknown")
                                zip_version   = mdata.get("Version",     "?")
                                zip_desc      = mdata.get("Description", "")
                            break
            except Exception:
                pass

            mods.append({
                "folder":       entry,
                "name":         manifest_name,
                "author":       zip_author,
                "version":      zip_version,
                "desc":         zip_desc,
                "unique_id":    "",
                "min_api":      "",
                "deps":         [],
                "enabled":      False,
                "folder_name":  name,
                "has_manifest": False,
                "is_zip":       True,
                "zip_path":     entry,
            })

    return mods


def install_zip_mod(zip_path: Path, mods_dir: Path) -> tuple[bool, str]:
    """
    Extract a mod ZIP into the Mods folder.
    Returns (success, message).
    Handles both flat ZIPs (manifest.json at root) and nested ZIPs
    (mod files inside a subfolder).
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

            # Detect if there's a top-level folder wrapping everything
            top_dirs = {n.split("/")[0] for n in names if "/" in n}
            all_in_one = (
                len(top_dirs) == 1 and
                all(n.startswith(list(top_dirs)[0] + "/") or n == list(top_dirs)[0] + "/"
                    for n in names)
            )

            if all_in_one:
                # ZIP already has a proper folder — extract directly to Mods
                zf.extractall(mods_dir)
                extracted_name = list(top_dirs)[0]
            else:
                # Flat ZIP — create a folder named after the ZIP
                dest_name = zip_path.stem
                dest = mods_dir / dest_name
                dest.mkdir(exist_ok=True)
                zf.extractall(dest)
                extracted_name = dest_name

        zip_path.unlink()  # Remove the ZIP after successful install
        return True, extracted_name
    except zipfile.BadZipFile:
        return False, "Not a valid ZIP file."
    except Exception as e:
        return False, str(e)


def mod_id(mod: dict) -> str:
    return mod["unique_id"] or mod["folder_name"].lstrip(".")


def find_steam_executable() -> str | None:
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
        candidates = [Path("/usr/bin/steam"), Path("/usr/local/bin/steam")]
        found = shutil.which("steam")
        if found:
            candidates.append(Path(found))
    for c in candidates:
        if c and c.exists():
            return str(c)
    return None


def launch_via_steam() -> subprocess.Popen | None:
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


def find_smapi_log() -> Path | None:
    for p in SMAPI_LOG_PATHS:
        if p.exists():
            return p
    return None


# ─── Profile Manager ──────────────────────────────────────────────────────────

class ProfileManager:
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

    def export_profile(self, name: str, path: Path):
        data = {"name": name, "enabled_mods": self.get(name),
                "exported_by": APP_NAME, "version": APP_VERSION,
                "exported_at": datetime.now().isoformat()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def import_profile(self, path: Path) -> str:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("name", path.stem)
        enabled = data.get("enabled_mods", [])
        # Avoid name collision
        base = name
        i = 1
        while name in self._data["profiles"]:
            name = f"{base} ({i})"
            i += 1
        self.save_profile(name, enabled)
        return name


# ─── Favourites ───────────────────────────────────────────────────────────────

class FavouritesManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._favs: set[str] = set()
        self._load()

    def _load(self):
        if FAVOURITES_FILE.exists():
            try:
                with open(FAVOURITES_FILE, encoding="utf-8") as f:
                    self._favs = set(json.load(f))
            except Exception:
                pass

    def _save(self):
        with open(FAVOURITES_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(self._favs), f, indent=2)

    def is_fav(self, mid: str) -> bool:
        return mid in self._favs

    def toggle(self, mid: str) -> bool:
        if mid in self._favs:
            self._favs.discard(mid)
        else:
            self._favs.add(mid)
        self._save()
        return mid in self._favs


# ─── Order Manager ────────────────────────────────────────────────────────────

class OrderManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._order: list[str] = []
        self._load()

    def _load(self):
        if ORDER_FILE.exists():
            try:
                with open(ORDER_FILE, encoding="utf-8") as f:
                    self._order = json.load(f)
            except Exception:
                pass

    def _save(self):
        with open(ORDER_FILE, "w", encoding="utf-8") as f:
            json.dump(self._order, f, indent=2)

    def sort_mods(self, mods: list[dict]) -> list[dict]:
        """Sort mods according to saved order, appending any new ones at end."""
        order_map = {mid: i for i, mid in enumerate(self._order)}
        return sorted(mods, key=lambda m: order_map.get(mod_id(m), 99999))

    def save_order(self, mods: list[dict]):
        self._order = [mod_id(m) for m in mods]
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
            result = subprocess.Popen(
                [self.smapi_path], cwd=str(Path(self.smapi_path).parent))
            self.finished.emit(f"Launched directly (PID {result.pid})")
        except Exception as e:
            self.error.emit(str(e))


# ─── Mod Details Panel ────────────────────────────────────────────────────────

class ModDetailsPanel(QWidget):
    """Right-hand panel showing full details for the selected mod."""

    fav_toggled = pyqtSignal(dict)

    def __init__(self, favs: FavouritesManager, parent=None):
        super().__init__(parent)
        self.favs = favs
        self.current_mod: dict | None = None
        self._build()

    def _build(self):
        self.setObjectName("DetailsPanel")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(12, 10, 8, 10)
        vl.setSpacing(8)

        # Placeholder
        self.placeholder = QLabel("← Select a mod\nto see details")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setFont(QFont("monospace", 10))
        self.placeholder.setStyleSheet(f"color:{P['text_dim']};")
        vl.addWidget(self.placeholder)

        # Details container (hidden until a mod is selected)
        self.details = QWidget()
        self.details.hide()
        dl = QVBoxLayout(self.details)
        dl.setContentsMargins(0,0,0,0)
        dl.setSpacing(6)

        # Name + fav button
        name_row = QHBoxLayout()
        self.name_lbl = QLabel()
        self.name_lbl.setFont(QFont("monospace", 12, QFont.Weight.Bold))
        self.name_lbl.setStyleSheet(f"color:{P['accent']};")
        self.name_lbl.setWordWrap(True)
        name_row.addWidget(self.name_lbl, 1)

        self.fav_btn = QPushButton("☆")
        self.fav_btn.setFixedSize(32, 32)
        self.fav_btn.setToolTip("Add to favourites")
        self.fav_btn.clicked.connect(self._toggle_fav)
        self.fav_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{P['accent2']};
                border:1px solid {P['border']}; border-radius:4px; font-size:16px;
            }}
            QPushButton:hover {{ border-color:{P['accent2']}; }}
        """)
        name_row.addWidget(self.fav_btn)
        dl.addLayout(name_row)

        self.author_lbl = QLabel()
        self.author_lbl.setFont(QFont("monospace", 9))
        self.author_lbl.setStyleSheet(f"color:{P['text_dim']};")
        dl.addWidget(self.author_lbl)

        self.ver_lbl = QLabel()
        self.ver_lbl.setFont(QFont("monospace", 9))
        self.ver_lbl.setStyleSheet(f"color:{P['text_dim']};")
        dl.addWidget(self.ver_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{P['border']};")
        dl.addWidget(sep)

        self.desc_lbl = QLabel()
        self.desc_lbl.setFont(QFont("monospace", 9))
        self.desc_lbl.setStyleSheet(f"color:{P['text']};")
        self.desc_lbl.setWordWrap(True)
        dl.addWidget(self.desc_lbl)

        # Metadata grid
        self.meta_box = QGroupBox("Info")
        meta_vl = QVBoxLayout(self.meta_box)
        meta_vl.setSpacing(4)
        self.uid_lbl      = self._meta_row(meta_vl, "UniqueID")
        self.minapi_lbl   = self._meta_row(meta_vl, "Min API")
        self.folder_lbl   = self._meta_row(meta_vl, "Folder")
        self.manifest_lbl = self._meta_row(meta_vl, "Manifest")
        dl.addWidget(self.meta_box)

        # Dependencies
        self.deps_box = QGroupBox("Dependencies")
        self.deps_vl = QVBoxLayout(self.deps_box)
        self.deps_vl.setSpacing(2)
        dl.addWidget(self.deps_box)

        dl.addStretch()
        vl.addWidget(self.details, 1)
        vl.addStretch()

    def _meta_row(self, parent_layout, label: str) -> QLabel:
        row = QHBoxLayout()
        lbl = QLabel(f"{label}:")
        lbl.setFont(QFont("monospace", 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color:{P['text_dim']};")
        lbl.setFixedWidth(70)
        row.addWidget(lbl)
        val = QLabel()
        val.setFont(QFont("monospace", 8))
        val.setStyleSheet(f"color:{P['text']};")
        val.setWordWrap(True)
        row.addWidget(val, 1)
        parent_layout.addLayout(row)
        return val

    def show_mod(self, mod: dict):
        self.current_mod = mod
        self.placeholder.hide()
        self.details.show()

        self.name_lbl.setText(mod["name"])
        self.author_lbl.setText(f"by {mod['author']}")
        self.ver_lbl.setText(f"Version {mod['version']}")
        self.desc_lbl.setText(mod["desc"] or "No description provided.")
        self.uid_lbl.setText(mod["unique_id"] or "—")
        self.minapi_lbl.setText(mod["min_api"] or "—")
        self.folder_lbl.setText(mod["folder_name"].lstrip("."))
        self.manifest_lbl.setText("✓ Present" if mod["has_manifest"] else "✗ Missing")
        self.manifest_lbl.setStyleSheet(
            f"color:{P['green']};" if mod["has_manifest"] else f"color:{P['red']};"
        )

        # Dependencies — only show what is actually in the manifest
        while self.deps_vl.count():
            item = self.deps_vl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        deps = [d for d in mod.get("deps", [])
                if isinstance(d, dict) and d.get("UniqueID")]

        if deps:
            for dep in deps:
                uid      = dep.get("UniqueID", "")
                ver_req  = dep.get("MinimumVersion", "")
                optional = not dep.get("IsRequired", True)
                parts    = [f"• {uid}"]
                if ver_req:
                    parts.append(f"≥ {ver_req}")
                if optional:
                    parts.append("(optional)")
                lbl = QLabel(" ".join(parts))
                lbl.setFont(QFont("monospace", 8))
                lbl.setStyleSheet(f"color:{P['text_dim']};")
                self.deps_vl.addWidget(lbl)
            self.deps_box.show()
        elif mod["has_manifest"]:
            none_lbl = QLabel("None declared in manifest.")
            none_lbl.setFont(QFont("monospace", 8))
            none_lbl.setStyleSheet(f"color:{P['text_dim']};")
            self.deps_vl.addWidget(none_lbl)
            self.deps_box.show()
        else:
            self.deps_box.hide()

        # Fav button
        mid = mod_id(mod)
        self.fav_btn.setText("★" if self.favs.is_fav(mid) else "☆")

    def _toggle_fav(self):
        if self.current_mod:
            self.favs.toggle(mod_id(self.current_mod))
            is_fav = self.favs.is_fav(mod_id(self.current_mod))
            self.fav_btn.setText("★" if is_fav else "☆")
            self.fav_toggled.emit(self.current_mod)

    def clear(self):
        self.current_mod = None
        self.placeholder.show()
        self.details.hide()


# ─── SMAPI Log Viewer ─────────────────────────────────────────────────────────

class LogViewer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SMAPI Log Viewer")
        self.setWindowIcon(make_icon())
        self.setMinimumSize(900, 600)
        self.setStyleSheet(f"""
            QDialog {{ background:{P['bg']}; color:{P['text']}; font-family:monospace; }}
        """)
        self._build()
        self._load_log()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("SMAPI Log Viewer")
        title.setFont(QFont("monospace", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{P['accent']};")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All levels", "ERROR only", "WARN+", "INFO+"])
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background:{P['surface2']}; color:{P['text']};
                border:1px solid {P['border']}; border-radius:4px; padding:3px 8px;
            }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{
                background:{P['surface2']}; color:{P['text']};
                border:1px solid {P['border']};
            }}
        """)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_combo)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search log…")
        self.search_box.setFixedWidth(180)
        self.search_box.textChanged.connect(self._apply_filter)
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                background:{P['surface2']}; border:1px solid {P['border']};
                border-radius:4px; color:{P['text']}; padding:3px 8px;
            }}
            QLineEdit:focus {{ border-color:{P['accent']}; }}
        """)
        toolbar.addWidget(self.search_box)

        reload_btn = QPushButton("↺ Reload")
        reload_btn.clicked.connect(self._load_log)
        reload_btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{P['blue']};
                border:1px solid {P['border']}; border-radius:4px; padding:4px 12px;
            }}
            QPushButton:hover {{ border-color:{P['blue']}; }}
        """)
        toolbar.addWidget(reload_btn)
        vl.addLayout(toolbar)

        # Log path label
        self.path_lbl = QLabel()
        self.path_lbl.setFont(QFont("monospace", 8))
        self.path_lbl.setStyleSheet(f"color:{P['text_dim']};")
        vl.addWidget(self.path_lbl)

        # Log display
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Courier New", 9))
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background:{P['surface']}; color:{P['text']};
                border:1px solid {P['border']}; border-radius:4px;
            }}
        """)
        vl.addWidget(self.log_view, 1)

        # Stats
        self.stats_lbl = QLabel()
        self.stats_lbl.setFont(QFont("monospace", 8))
        self.stats_lbl.setStyleSheet(f"color:{P['text_dim']};")
        vl.addWidget(self.stats_lbl)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{P['text']};
                border:1px solid {P['border']}; border-radius:4px; padding:6px 20px;
            }}
            QPushButton:hover {{ border-color:{P['accent']}; }}
        """)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        vl.addLayout(btn_row)

        self._raw_lines: list[str] = []

    def _load_log(self):
        log_path = find_smapi_log()
        if not log_path:
            self.path_lbl.setText("SMAPI log not found. Launch the game at least once.")
            self.log_view.setPlainText("")
            return
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                self._raw_lines = f.readlines()
            self.path_lbl.setText(f"Log: {log_path}")
            self._apply_filter()
        except Exception as e:
            self.path_lbl.setText(f"Error reading log: {e}")

    def _colour_for_line(self, line: str) -> str:
        """Return the Windows Terminal–accurate colour for a SMAPI log line."""
        # Check override keywords first (exceptions etc.)
        for keyword, col in LOG_LINE_OVERRIDES.items():
            if keyword in line:
                return col
        # Match level tags in priority order
        for tag in ("[ERROR]", "[WARN]", "[TRACE]", "[DEBUG]", "[INFO]",
                    "[ALL]", "[SMAPI]", "[game]", "[Content]",
                    "[ConsoleCommands]", "[SaveBackup]"):
            if tag in line:
                return LOG_COLOURS.get(tag, "#cccccc")
        return "#cccccc"   # default terminal text colour

    def _apply_filter(self):
        level  = self.filter_combo.currentIndex()
        query  = self.search_box.text().lower()
        errors = warnings = 0

        html_lines = []
        for line in self._raw_lines:
            is_error = "[ERROR]" in line
            is_warn  = "[WARN]"  in line
            is_info  = "[INFO]"  in line or "[SMAPI]" in line or "[game]" in line
            if level == 1 and not is_error:
                continue
            if level == 2 and not (is_error or is_warn):
                continue
            if level == 3 and not (is_error or is_warn or is_info):
                continue
            if query and query not in line.lower():
                continue

            if is_error: errors += 1
            if is_warn:  warnings += 1

            colour = self._colour_for_line(line)
            safe = (line.rstrip()
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))

            if query:
                idx = safe.lower().find(query)
                if idx >= 0:
                    safe = (safe[:idx]
                        + f"<span style='background:#3a3a1a;color:#ffffff;'>"
                        + f"{safe[idx:idx+len(query)]}</span>"
                        + safe[idx+len(query):])

            html_lines.append(f"<span style='color:{colour};'>{safe}</span>")

        # Dark terminal background for log area
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background:#0c0c0c; color:#cccccc;
                border:1px solid {P['border']}; border-radius:4px;
                font-family:'Cascadia Code','Consolas','Courier New',monospace;
                font-size:9pt;
            }}
        """)
        self.log_view.setHtml(
            "<pre style='font-family:Cascadia Code,Consolas,Courier New,monospace;"
            "font-size:9pt;background:#0c0c0c;color:#cccccc;margin:0;padding:4px;'>"
            + "<br>".join(html_lines) + "</pre>"
        )
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

        total = len(html_lines)
        self.stats_lbl.setText(
            f"{total} lines shown  ·  "
            f"<span style='color:#c50f1f'>{errors} errors</span>  ·  "
            f"<span style='color:#c19c00'>{warnings} warnings</span>"
        )
        self.stats_lbl.setTextFormat(Qt.TextFormat.RichText)



# ─── ZIP Mod Card ─────────────────────────────────────────────────────────────

class ZipModCard(QWidget):
    """Card shown for .zip files sitting in the Mods folder, with an Unzip button."""
    unzip_requested = pyqtSignal(dict)

    def __init__(self, mod: dict, parent=None):
        super().__init__(parent)
        self.mod = mod
        self._build()

    def _build(self):
        self.setObjectName("ZipCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # ZIP icon
        icon = QLabel("📦")
        icon.setFont(QFont("monospace", 16))
        icon.setFixedWidth(28)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        name_row = QHBoxLayout()
        name_lbl = QLabel(self.mod["name"])
        name_lbl.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color:{P['accent2']};")
        name_row.addWidget(name_lbl)
        name_row.addStretch()

        size_bytes = self.mod["zip_path"].stat().st_size
        size_str = (f"{size_bytes/1024/1024:.1f} MB" if size_bytes > 1024*1024
                    else f"{size_bytes/1024:.0f} KB")
        size_lbl = QLabel(size_str)
        size_lbl.setFont(QFont("monospace", 8))
        size_lbl.setStyleSheet(f"color:{P['text_dim']};")
        name_row.addWidget(size_lbl)
        text_col.addLayout(name_row)

        sub_row = QHBoxLayout()
        if self.mod["author"] != "Unknown":
            auth_lbl = QLabel(f"by {self.mod['author']}")
            auth_lbl.setFont(QFont("monospace", 8))
            auth_lbl.setStyleSheet(f"color:{P['text_dim']};")
            sub_row.addWidget(auth_lbl)
        zip_tag = QLabel("ZIP — ready to install")
        zip_tag.setFont(QFont("monospace", 8))
        zip_tag.setStyleSheet(f"color:{P['orange']};")
        sub_row.addWidget(zip_tag)
        sub_row.addStretch()
        text_col.addLayout(sub_row)
        layout.addLayout(text_col, 1)

        # Unzip button
        unzip_btn = QPushButton("📦 Unzip & Install")
        unzip_btn.setFixedHeight(30)
        unzip_btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{P['accent2']};
                border:1px solid {P['accent2']}; border-radius:5px;
                padding:0 12px; font-size:11px; font-weight:bold;
            }}
            QPushButton:hover   {{ background:#3a3020; }}
            QPushButton:pressed {{ background:{P['bg']}; }}
        """)
        unzip_btn.clicked.connect(lambda: self.unzip_requested.emit(self.mod))
        layout.addWidget(unzip_btn)

        self.setStyleSheet(f"""
            #ZipCard {{
                background:#1e1e14;
                border:1px dashed {P['accent2']};
                border-radius:6px;
            }}
        """)

# ─── Mod Card (drag-enabled) ──────────────────────────────────────────────────

class ModCard(QWidget):
    toggle_requested  = pyqtSignal(dict, bool)
    selected          = pyqtSignal(dict)
    drag_started      = pyqtSignal(QWidget)

    def __init__(self, mod: dict, favs: FavouritesManager, parent=None):
        super().__init__(parent)
        self.mod        = mod
        self.favs       = favs
        self._dragging  = False
        self._drag_start_pos = None
        self._selected  = False
        self._build()

    def _build(self):
        self.setObjectName("ModCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Drag handle
        drag_lbl = QLabel("⠿")
        drag_lbl.setFixedWidth(14)
        drag_lbl.setStyleSheet(f"color:{P['border']}; font-size:14px;")
        drag_lbl.setToolTip("Drag to reorder")
        layout.addWidget(drag_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        # Favourite star
        self.fav_lbl = QLabel()
        self.fav_lbl.setFixedWidth(16)
        self.fav_lbl.setFont(QFont("monospace", 10))
        self._update_fav()
        layout.addWidget(self.fav_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        # Toggle
        self.toggle = QCheckBox()
        self.toggle.setChecked(self.mod["enabled"])
        self.toggle.setFixedSize(20, 20)
        self.toggle.toggled.connect(lambda v: self.toggle_requested.emit(self.mod, v))
        layout.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)

        # Status dot
        self.dot = QLabel("●")
        self.dot.setFixedWidth(14)
        self._update_dot()
        layout.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        name_row = QHBoxLayout()
        self.name_lbl = QLabel(self.mod["name"])
        self.name_lbl.setFont(QFont("monospace", 10, QFont.Weight.Bold))
        name_row.addWidget(self.name_lbl)
        name_row.addStretch()

        if not self.mod["has_manifest"]:
            warn = QLabel("⚠ no manifest")
            warn.setFont(QFont("monospace", 8))
            warn.setStyleSheet(f"color:{P['orange']};")
            name_row.addWidget(warn)

        self.ver_lbl = QLabel(f"v{self.mod['version']}")
        self.ver_lbl.setFont(QFont("monospace", 8))
        self.ver_lbl.setStyleSheet(f"color:{P['text_dim']};")
        name_row.addWidget(self.ver_lbl)
        text_col.addLayout(name_row)

        self.auth_lbl = QLabel(f"by {self.mod['author']}")
        self.auth_lbl.setFont(QFont("monospace", 8))
        self.auth_lbl.setStyleSheet(f"color:{P['text_dim']};")
        text_col.addWidget(self.auth_lbl)
        layout.addLayout(text_col, 1)

        self._style()

    def _update_dot(self):
        c = P["green"] if self.mod["enabled"] else P["red"]
        self.dot.setStyleSheet(f"color:{c}; font-size:10px;")

    def _update_fav(self):
        mid = mod_id(self.mod)
        if self.favs.is_fav(mid):
            self.fav_lbl.setText("★")
            self.fav_lbl.setStyleSheet(f"color:{P['accent2']};")
        else:
            self.fav_lbl.setText("")

    def _style(self):
        en  = self.mod["enabled"]
        bg  = P["surface2"]   if en else P["disabled_bg"]
        brd = P["accent"]     if (self._selected) else (P["accent"] if en else P["border"])
        if self._selected:
            bg = "#263526"
        self.setStyleSheet(f"""
            #ModCard {{ background:{bg}; border:1px solid {brd}; border-radius:6px; }}
            QCheckBox::indicator {{
                width:16px; height:16px;
                border:2px solid {P['border']}; border-radius:3px; background:{P['surface']};
            }}
            QCheckBox::indicator:checked {{
                background:{P['accent']}; border-color:{P['accent']};
            }}
        """)

    def set_selected(self, sel: bool):
        self._selected = sel
        self._style()

    def refresh(self, mod: dict):
        self.mod = mod
        self.toggle.blockSignals(True)
        self.toggle.setChecked(mod["enabled"])
        self.toggle.blockSignals(False)
        self.name_lbl.setText(mod["name"])
        self.ver_lbl.setText(f"v{mod['version']}")
        self.auth_lbl.setText(f"by {mod['author']}")
        self._update_dot()
        self._update_fav()
        self._style()

    def refresh_fav(self):
        self._update_fav()

    # Drag support
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton and
                self._drag_start_pos is not None and
                (event.pos() - self._drag_start_pos).manhattanLength() > 10):
            self.drag_started.emit(self)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = None
            self.selected.emit(self.mod)
        super().mouseReleaseEvent(event)


# ─── Draggable Mod List ───────────────────────────────────────────────────────

class DraggableModList(QWidget):
    """Container that holds ModCards and supports drag-to-reorder."""

    order_changed    = pyqtSignal()
    mod_selected     = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(5)
        self._layout.addStretch()
        self._cards: list[ModCard] = []
        self._drag_card: ModCard | None = None
        self._selected_card: ModCard | None = None

    def set_cards(self, cards: list[ModCard], zip_cards: list = None):
        # Clear all widgets
        for card in self._cards:
            self._layout.removeWidget(card)
            card.deleteLater()
        for zc in getattr(self, "_zip_cards", []):
            self._layout.removeWidget(zc)
            zc.deleteLater()
        self._cards = []
        self._zip_cards = zip_cards or []
        self._selected_card = None

        # Remove stretch
        if self._layout.count():
            self._layout.takeAt(self._layout.count() - 1)

        # ZIP cards first (top of list) with a separator if any exist
        if self._zip_cards:
            sep_lbl = QLabel("  📦  ZIPs ready to install")
            sep_lbl.setFont(QFont("monospace", 8))
            sep_lbl.setStyleSheet(f"color:{P['accent2']}; padding:2px 0;")
            self._layout.addWidget(sep_lbl)
            self._zip_cards.insert(0, sep_lbl)  # track for cleanup
            for zc in self._zip_cards[1:]:
                self._layout.addWidget(zc)

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"color:{P['border']}; margin:4px 0;")
            self._layout.addWidget(sep)
            self._zip_cards.append(sep)

        for card in cards:
            card.drag_started.connect(self._on_drag_started)
            card.selected.connect(self._on_card_selected)
            self._layout.addWidget(card)
            self._cards.append(card)

        self._layout.addStretch()

    def _on_drag_started(self, card: ModCard):
        self._drag_card = card

    def _on_card_selected(self, mod: dict):
        # Deselect old
        if self._selected_card:
            self._selected_card.set_selected(False)
        # Find new
        for card in self._cards:
            if card.mod is mod:
                card.set_selected(True)
                self._selected_card = card
                break
        self.mod_selected.emit(mod)

    def dragEnterEvent(self, event):
        if self._drag_card:
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if not self._drag_card:
            return
        # Find drop position
        drop_y = event.position().y()
        target_idx = len(self._cards)
        for i, card in enumerate(self._cards):
            if drop_y < card.y() + card.height() / 2:
                target_idx = i
                break

        old_idx = self._cards.index(self._drag_card)
        if old_idx == target_idx or old_idx == target_idx - 1:
            self._drag_card = None
            return

        # Reorder
        card = self._cards.pop(old_idx)
        if target_idx > old_idx:
            target_idx -= 1
        self._cards.insert(target_idx, card)

        # Rebuild layout
        self._layout.takeAt(self._layout.count() - 1)
        for c in self._cards:
            self._layout.removeWidget(c)
        for c in self._cards:
            self._layout.addWidget(c)
        self._layout.addStretch()

        self._drag_card = None
        self.order_changed.emit()
        event.acceptProposedAction()

    def mouseMoveEvent(self, event):
        if self._drag_card:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText("mod_drag")
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)

    def get_cards(self) -> list[ModCard]:
        return list(self._cards)

    def deselect_all(self):
        for card in self._cards:
            card.set_selected(False)
        self._selected_card = None


# ─── Profiles Panel ───────────────────────────────────────────────────────────

class ProfilesPanel(QWidget):
    profile_applied = pyqtSignal(str)

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
        self.btn_new = self._sbtn("＋", P["green"])
        self.btn_new.setToolTip("New profile")
        self.btn_new.clicked.connect(self._new_profile)
        hdr.addWidget(self.btn_new)

        import_btn = self._sbtn("↓", P["blue"])
        import_btn.setToolTip("Import profile from file")
        import_btn.clicked.connect(self._import_profile)
        hdr.addWidget(import_btn)
        vl.addLayout(hdr)

        self.list_area = QVBoxLayout()
        self.list_area.setSpacing(4)
        vl.addLayout(self.list_area)
        vl.addStretch()
        self._rebuild()

    def _sbtn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedSize(26, 26)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{color};
                border:1px solid {P['border']}; border-radius:4px; font-size:12px;
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
            empty = QLabel("No profiles yet.\nClick ＋ to create one.")
            empty.setFont(QFont("monospace", 8))
            empty.setStyleSheet(f"color:{P['text_dim']};")
            empty.setWordWrap(True)
            self.list_area.addWidget(empty)
            return

        for name in self.profiles.names():
            is_active = (name == active)
            enabled_count = len(self.profiles.get(name))

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
            rl.setContentsMargins(8, 4, 8, 4)
            rl.setSpacing(4)

            dot = QLabel("●")
            dot.setFixedWidth(12)
            dot.setStyleSheet(f"color:{P['accent'] if is_active else P['border']}; font-size:8px;")
            rl.addWidget(dot)

            name_col = QVBoxLayout()
            nm = QLabel(name)
            nm.setFont(QFont("monospace", 9, QFont.Weight.Bold if is_active else QFont.Weight.Normal))
            nm.setStyleSheet(f"color:{P['accent'] if is_active else P['text']};")
            name_col.addWidget(nm)
            count_lbl = QLabel(f"{enabled_count} mod{'s' if enabled_count != 1 else ''}")
            count_lbl.setFont(QFont("monospace", 7))
            count_lbl.setStyleSheet(f"color:{P['text_dim']};")
            name_col.addWidget(count_lbl)
            rl.addLayout(name_col, 1)

            apply_btn = QPushButton("Apply")
            apply_btn.setFixedHeight(22)
            apply_btn.setStyleSheet(f"""
                QPushButton {{
                    background:{P['surface2']}; color:{P['accent']};
                    border:1px solid {P['border']}; border-radius:3px; font-size:9px; padding:0 6px;
                }}
                QPushButton:hover {{ border-color:{P['accent']}; }}
            """)
            apply_btn.clicked.connect(lambda _, n=name: self._apply(n))
            rl.addWidget(apply_btn)

            more_btn = QPushButton("⋮")
            more_btn.setFixedSize(22, 22)
            more_btn.setStyleSheet(f"""
                QPushButton {{
                    background:{P['surface2']}; color:{P['text_dim']};
                    border:1px solid {P['border']}; border-radius:3px; font-size:12px;
                }}
                QPushButton:hover {{ border-color:{P['text_dim']}; }}
            """)
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
                QMessageBox.warning(self, "Duplicate", f"'{name}' already exists.")
                return
            self.profile_applied.emit(f"__save__:{name}")
            self._rebuild()

    def _import_profile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", str(Path.home()), "Profile Files (*.json)")
        if path:
            try:
                name = self.profiles.import_profile(Path(path))
                self._rebuild()
                QMessageBox.information(self, "Imported",
                    f"Profile '{name}' imported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", str(e))

    def _menu(self, name: str, btn: QPushButton):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{P['surface2']}; color:{P['text']};
                border:1px solid {P['border']}; border-radius:4px; padding:4px; }}
            QMenu::item {{ padding:4px 14px; border-radius:3px; }}
            QMenu::item:selected {{ background:{P['surface']}; color:{P['accent']}; }}
        """)
        rename_act    = menu.addAction("✏  Rename")
        overwrite_act = menu.addAction("💾  Overwrite with current mods")
        export_act    = menu.addAction("↑  Export to file")
        menu.addSeparator()
        delete_act = menu.addAction("🗑  Delete")

        action = menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))

        if action == rename_act:
            new_name, ok = QInputDialog.getText(
                self, "Rename", "New name:", text=name)
            if ok and new_name.strip() and new_name.strip() != name:
                self.profiles.rename_profile(name, new_name.strip())
                self._rebuild()
        elif action == overwrite_act:
            self.profile_applied.emit(f"__save__:{name}")
        elif action == export_act:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Profile", str(Path.home() / f"{name}.json"),
                "Profile Files (*.json)")
            if path:
                self.profiles.export_profile(name, Path(path))
                QMessageBox.information(self, "Exported",
                    f"Profile exported to:\n{path}")
        elif action == delete_act:
            if QMessageBox.question(self, "Delete",
                    f"Delete profile '{name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes:
                self.profiles.delete_profile(name)
                self._rebuild()

    def refresh(self):
        self._rebuild()


# ─── First Launch Dialog ──────────────────────────────────────────────────────

class FirstLaunchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mods_dir   = ""
        self.smapi_path = ""
        self.setWindowTitle(f"Welcome to {APP_NAME}")
        self.setWindowIcon(make_icon())
        self.setMinimumWidth(580)
        self.setModal(True)
        self._build()

    def _auto_detect(self) -> tuple[str, str]:
        """Try to find Mods dir and SMAPI path automatically."""
        found_mods  = ""
        found_smapi = ""
        for p in DEFAULT_MOD_PATHS:
            if p.exists():
                found_mods = str(p)
                break
        for p in DEFAULT_SMAPI_PATHS:
            if p.exists():
                found_smapi = str(p)
                break
        return found_mods, found_smapi

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setSpacing(14)
        vl.setContentsMargins(24, 24, 24, 24)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon().pixmap(48, 48))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(icon_lbl)

        title = QLabel(f"Welcome to {APP_NAME}!")
        title.setFont(QFont("monospace", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color:{P['accent']};")
        vl.addWidget(title)

        # Auto-detect paths and show result
        auto_mods, auto_smapi = self._auto_detect()
        if auto_mods and auto_smapi:
            detect_msg = "✓  Stardew Valley found automatically!"
            detect_col = P["green"]
        elif auto_mods or auto_smapi:
            detect_msg = "⚠  Partially detected — please verify the paths below."
            detect_col = P["accent2"]
        else:
            detect_msg = "✗  Could not auto-detect Stardew Valley. Please set paths manually."
            detect_col = P["red"]

        detect_lbl = QLabel(detect_msg)
        detect_lbl.setFont(QFont("monospace", 9, QFont.Weight.Bold))
        detect_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detect_lbl.setStyleSheet(f"color:{detect_col};")
        detect_lbl.setWordWrap(True)
        vl.addWidget(detect_lbl)

        sub = QLabel("You can adjust the paths below if anything looks wrong.")
        sub.setFont(QFont("monospace", 9))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{P['text_dim']};")
        sub.setWordWrap(True)
        vl.addWidget(sub)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color:{P['border']};")
        vl.addWidget(line)

        fs = (f"background:{P['surface2']}; border:1px solid {P['border']};"
              f"border-radius:4px; color:{P['text']}; padding:4px 8px; font-size:11px;")
        bs = (f"QPushButton {{ background:{P['surface2']}; color:{P['text']};"
              f"border:1px solid {P['border']}; border-radius:4px; padding:4px 14px; }}"
              f"QPushButton:hover {{ border-color:{P['accent']}; }}")

        for attr, label, hint, is_file, default_val in [
            ("mods", "📁  Mods Directory",
             "The 'Mods' folder inside your Stardew Valley installation.",
             False, auto_mods),
            ("smapi", "⚙️  SMAPI Executable",
             "The StardewModdingAPI file (StardewModdingAPI.exe on Windows).",
             True, auto_smapi),
        ]:
            lbl = QLabel(label)
            lbl.setFont(QFont("monospace", 10, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color:{P['accent2']};")
            vl.addWidget(lbl)
            hint_lbl = QLabel(hint)
            hint_lbl.setFont(QFont("monospace", 8))
            hint_lbl.setStyleSheet(f"color:{P['text_dim']};")
            vl.addWidget(hint_lbl)
            row = QHBoxLayout()
            edit = QLineEdit()
            edit.setText(default_val)   # pre-fill with auto-detected path
            edit.setPlaceholderText("Click Browse…")
            edit.setStyleSheet(fs)
            edit.textChanged.connect(self._validate)
            setattr(self, f"{attr}_edit", edit)
            row.addWidget(edit, 1)
            btn = QPushButton("Browse…")
            btn.setStyleSheet(bs)
            if is_file:
                btn.clicked.connect(lambda _, e=edit: e.setText(
                    QFileDialog.getOpenFileName(self, "Select SMAPI", str(Path.home()))[0] or e.text()))
            else:
                btn.clicked.connect(lambda _, e=edit: e.setText(
                    QFileDialog.getExistingDirectory(self, "Select Mods folder", str(Path.home())) or e.text()))
            row.addWidget(btn)
            vl.addLayout(row)
            status = QLabel("")
            status.setFont(QFont("monospace", 8))
            setattr(self, f"{attr}_status", status)
            vl.addWidget(status)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"color:{P['border']};")
        vl.addWidget(line2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        skip = QPushButton("Skip for now")
        skip.setFixedHeight(34)
        skip.setStyleSheet(f"QPushButton {{ background:{P['surface2']}; color:{P['text_dim']};"
                           f"border:1px solid {P['border']}; border-radius:5px; padding:0 16px; }}")
        skip.clicked.connect(self.reject)
        btn_row.addWidget(skip)

        self.ok_btn = QPushButton("✓  Let's Go!")
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

        self.setStyleSheet(f"QDialog {{ background:{P['bg']}; color:{P['text']}; font-family:monospace; }}")
        # Validate pre-filled paths so status labels are shown immediately
        QTimer.singleShot(0, self._validate)

    def _validate(self):
        mods_ok  = bool(self.mods_edit.text().strip()  and Path(self.mods_edit.text().strip()).exists())
        smapi_ok = bool(self.smapi_edit.text().strip() and Path(self.smapi_edit.text().strip()).exists())
        for ok, status in [(mods_ok, self.mods_status), (smapi_ok, self.smapi_status)]:
            edit = self.mods_edit if status is self.mods_status else self.smapi_edit
            if edit.text().strip():
                status.setText("✓  Found!" if ok else "✗  Not found")
                status.setStyleSheet(f"color:{P['green']};" if ok else f"color:{P['red']};")
            else:
                status.setText("")
        self.ok_btn.setEnabled(mods_ok and smapi_ok)

    def _accept(self):
        self.mods_dir   = self.mods_edit.text().strip()
        self.smapi_path = self.smapi_edit.text().strip()
        self.accept()


# ─── Main Window ──────────────────────────────────────────────────────────────

class SDVModManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings    = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.profiles    = ProfileManager()
        self.favs        = FavouritesManager()
        self.order_mgr   = OrderManager()
        self.mods_dir:   Path | None = None
        self.smapi_path: str = ""
        self.mods:       list[dict] = []
        self.mod_cards:  list[ModCard] = []
        self._load_settings()
        self._build_ui()
        self._apply_theme()
        self.refresh_mods()
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
                    self.mods_dir = p; break
        if saved_smapi and Path(saved_smapi).exists():
            self.smapi_path = saved_smapi
        else:
            for p in DEFAULT_SMAPI_PATHS:
                if p.exists():
                    self.smapi_path = str(p); break

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
        self.setMinimumSize(1000, 660)
        self.resize(int(self.settings.value("width", 1200)),
                    int(self.settings.value("height", 740)))

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
        header.setFixedHeight(60)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(make_icon().pixmap(36, 36))
        hl.addWidget(icon_lbl)
        hl.addSpacing(8)

        title = QLabel(APP_NAME)
        title.setFont(QFont("monospace", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{P['accent']}; letter-spacing:1px;")
        hl.addWidget(title)

        sub = QLabel(f"v{APP_VERSION}")
        sub.setFont(QFont("monospace", 9))
        sub.setStyleSheet(f"color:{P['text_dim']};")
        sub.setAlignment(Qt.AlignmentFlag.AlignBottom)
        hl.addWidget(sub)
        hl.addStretch()

        plat_lbl = QLabel(PLATFORM)
        plat_lbl.setFont(QFont("monospace", 9))
        plat_lbl.setStyleSheet(f"color:{P['blue']}; background:{P['surface2']};"
                               f"border:1px solid {P['border']}; border-radius:8px; padding:2px 8px;")
        hl.addWidget(plat_lbl)
        hl.addSpacing(6)

        self.count_label = QLabel("0 mods")
        self.count_label.setFont(QFont("monospace", 10))
        self.count_label.setStyleSheet(f"color:{P['text_dim']}; background:{P['surface2']};"
                                       f"border:1px solid {P['border']}; border-radius:10px; padding:2px 10px;")
        hl.addWidget(self.count_label)
        return header

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("Toolbar")
        bar.setFixedHeight(50)
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(16, 6, 16, 6)
        hl.setSpacing(6)

        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search mods…")
        self.search.setFixedWidth(200)
        self.search.textChanged.connect(self._rebuild_cards)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background:{P['surface2']}; border:1px solid {P['border']};
                border-radius:6px; color:{P['text']}; padding:4px 10px; font-size:11px;
            }}
            QLineEdit:focus {{ border-color:{P['accent']}; }}
        """)
        hl.addWidget(self.search)

        # Sort
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Custom order", "Name A–Z", "Name Z–A",
                                  "Author A–Z", "Enabled first", "Disabled first", "Favourites first"])
        self.sort_combo.setFixedWidth(150)
        self.sort_combo.currentIndexChanged.connect(self._rebuild_cards)
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                background:{P['surface2']}; color:{P['text']};
                border:1px solid {P['border']}; border-radius:5px; padding:3px 8px; font-size:11px;
            }}
            QComboBox::drop-down {{ border:none; width:20px; }}
            QComboBox QAbstractItemView {{
                background:{P['surface2']}; color:{P['text']};
                border:1px solid {P['border']}; selection-background-color:{P['surface']};
            }}
        """)
        hl.addWidget(self.sort_combo)

        # Filter
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All mods", "Enabled only", "Disabled only",
                                    "Favourites", "Missing manifest"])
        self.filter_combo.setFixedWidth(150)
        self.filter_combo.currentIndexChanged.connect(self._rebuild_cards)
        self.filter_combo.setStyleSheet(self.sort_combo.styleSheet())
        hl.addWidget(self.filter_combo)

        hl.addStretch()

        self.btn_enable_all  = self._tbtn("Enable All",  P["green"])
        self.btn_enable_all.clicked.connect(self._enable_all)
        hl.addWidget(self.btn_enable_all)

        self.btn_disable_all = self._tbtn("Disable All", P["red"])
        self.btn_disable_all.clicked.connect(self._disable_all)
        hl.addWidget(self.btn_disable_all)

        hl.addWidget(self._sep())

        self.btn_log = self._tbtn("📋 Log", P["blue"])
        self.btn_log.clicked.connect(self._show_log)
        hl.addWidget(self.btn_log)

        self.btn_paths = self._tbtn("⚙  Paths", P["text_dim"])
        self.btn_paths.clicked.connect(self._show_paths_dialog)
        hl.addWidget(self.btn_paths)

        self.btn_refresh = self._tbtn("↺", P["blue"])
        self.btn_refresh.setToolTip("Refresh mod list")
        self.btn_refresh.setFixedWidth(34)
        self.btn_refresh.clicked.connect(self.refresh_mods)
        hl.addWidget(self.btn_refresh)

        hl.addWidget(self._sep())

        self.btn_launch = QPushButton("▶  Launch with SMAPI")
        self.btn_launch.setFixedHeight(34)
        self.btn_launch.clicked.connect(self._launch_smapi)
        self.btn_launch.setStyleSheet(f"""
            QPushButton {{
                background:{P['accent']}; color:#1a1c23; border:none;
                border-radius:6px; padding:0 16px; font-size:12px; font-weight:bold;
            }}
            QPushButton:hover    {{ background:#96c896; }}
            QPushButton:pressed  {{ background:#5a9a5a; }}
            QPushButton:disabled {{ background:{P['border']}; color:{P['text_dim']}; }}
        """)
        hl.addWidget(self.btn_launch)
        return bar

    def _tbtn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{color};
                border:1px solid {P['border']}; border-radius:5px; padding:0 10px; font-size:11px;
            }}
            QPushButton:hover   {{ background:{P['surface']}; border-color:{color}; }}
            QPushButton:pressed {{ background:{P['bg']}; }}
        """)
        return btn

    def _sep(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{P['border']};")
        return sep

    def _build_content(self) -> QWidget:
        container = QWidget()
        hl = QHBoxLayout(container)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(8)

        # ── Left: mod list ────────────────────────────────────────────────────
        left = QWidget()
        left_vl = QVBoxLayout(left)
        left_vl.setContentsMargins(0,0,0,0)
        left_vl.setSpacing(4)

        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("monospace", 9))
        self.stats_label.setStyleSheet(f"color:{P['text_dim']}; padding-left:2px;")
        left_vl.addWidget(self.stats_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background:transparent; border:none; }}
            QScrollBar:vertical {{ background:{P['surface']}; width:8px; border-radius:4px; }}
            QScrollBar::handle:vertical {{ background:{P['border']}; border-radius:4px; min-height:24px; }}
            QScrollBar::handle:vertical:hover {{ background:{P['accent']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)

        self.mod_list = DraggableModList()
        self.mod_list.setStyleSheet("background:transparent;")
        self.mod_list.order_changed.connect(self._on_order_changed)
        self.mod_list.mod_selected.connect(self._on_mod_selected)
        scroll.setWidget(self.mod_list)
        left_vl.addWidget(scroll, 1)

        # ── Middle: details panel ─────────────────────────────────────────────
        self.details_panel = ModDetailsPanel(self.favs)
        self.details_panel.setFixedWidth(240)
        self.details_panel.fav_toggled.connect(self._on_fav_toggled)

        # ── Right: sidebar ────────────────────────────────────────────────────
        right = QWidget()
        right.setFixedWidth(220)
        right_vl = QVBoxLayout(right)
        right_vl.setContentsMargins(4,0,0,0)
        right_vl.setSpacing(8)

        # Profiles
        prof_box = QGroupBox("Profiles")
        pb_vl = QVBoxLayout(prof_box)
        pb_vl.setContentsMargins(6,6,6,6)
        self.profiles_panel = ProfilesPanel(self.profiles)
        self.profiles_panel.profile_applied.connect(self._on_profile_signal)
        pb_vl.addWidget(self.profiles_panel)

        save_btn = QPushButton("💾  Save current as profile")
        save_btn.setFixedHeight(26)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background:{P['surface2']}; color:{P['accent2']};
                border:1px solid {P['border']}; border-radius:4px; font-size:10px;
            }}
            QPushButton:hover {{ border-color:{P['accent2']}; }}
        """)
        save_btn.clicked.connect(self._save_current_as_profile)
        pb_vl.addWidget(save_btn)
        right_vl.addWidget(prof_box)

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
        right_vl.addWidget(paths_box)

        # Legend
        legend_box = QGroupBox("Legend")
        leg_vl = QVBoxLayout(legend_box)
        for sym, lbl, col in [("●","Enabled",P["green"]),("●","Disabled",P["red"]),
                               ("★","Favourite",P["accent2"]),("⚠","No manifest",P["orange"])]:
            row = QHBoxLayout()
            d = QLabel(sym)
            d.setFixedWidth(16)
            d.setStyleSheet(f"color:{col}; font-size:10px;")
            row.addWidget(d)
            t = QLabel(lbl)
            t.setFont(QFont("monospace", 8))
            t.setStyleSheet(f"color:{P['text_dim']};")
            row.addWidget(t)
            row.addStretch()
            leg_vl.addLayout(row)
        right_vl.addWidget(legend_box)
        right_vl.addStretch()

        hl.addWidget(left, 1)
        hl.addWidget(self.details_panel)
        hl.addWidget(right)
        return container

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{P['bg']}; color:{P['text']}; font-family:monospace; }}
            #Header  {{ background:{P['surface']}; border-bottom:1px solid {P['border']}; }}
            #Toolbar {{ background:{P['surface']}; border-bottom:1px solid {P['border']}; }}
            #DetailsPanel {{ background:{P['surface']}; border-left:1px solid {P['border']}; border-radius:0; }}
            QGroupBox {{
                background:{P['surface']}; border:1px solid {P['border']};
                border-radius:6px; margin-top:12px; padding:6px; color:{P['accent2']};
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
        self.details_panel.clear()
        n = len(self.mods)
        self.status.showMessage(
            f"Loaded {n} mod{'s' if n!=1 else ''} from {self.mods_dir or '(no path set)'}")

    def _apply_sort_filter(self, mods: list[dict]) -> list[dict]:
        query   = self.search.text().lower()
        sort_i  = self.sort_combo.currentIndex()
        filter_i = self.filter_combo.currentIndex()

        # Filter
        result = []
        for m in mods:
            if query and query not in m["name"].lower() and query not in m["author"].lower():
                continue
            if filter_i == 1 and not m["enabled"]:
                continue
            if filter_i == 2 and m["enabled"]:
                continue
            if filter_i == 3 and not self.favs.is_fav(mod_id(m)):
                continue
            if filter_i == 4 and m["has_manifest"]:
                continue
            result.append(m)

        # Sort
        if sort_i == 0:   # Custom order
            result = self.order_mgr.sort_mods(result)
        elif sort_i == 1: # Name A-Z
            result.sort(key=lambda m: m["name"].lower())
        elif sort_i == 2: # Name Z-A
            result.sort(key=lambda m: m["name"].lower(), reverse=True)
        elif sort_i == 3: # Author A-Z
            result.sort(key=lambda m: m["author"].lower())
        elif sort_i == 4: # Enabled first
            result.sort(key=lambda m: not m["enabled"])
        elif sort_i == 5: # Disabled first
            result.sort(key=lambda m: m["enabled"])
        elif sort_i == 6: # Favourites first
            result.sort(key=lambda m: not self.favs.is_fav(mod_id(m)))

        return result

    def _rebuild_cards(self):
        visible_mods = self._apply_sort_filter(self.mods)
        cards = []
        zip_cards = []

        for mod in visible_mods:
            if mod["is_zip"]:
                # ZIP cards go in a separate list, shown at top
                zcard = ZipModCard(mod)
                zcard.unzip_requested.connect(self._on_unzip)
                zip_cards.append(zcard)
            else:
                card = ModCard(mod, self.favs)
                card.toggle_requested.connect(self._on_toggle)
                cards.append(card)

        self.mod_list.set_cards(cards, zip_cards)
        self.mod_cards = cards
        self._update_stats()

    def _on_mod_selected(self, mod: dict):
        self.details_panel.show_mod(mod)

    def _on_fav_toggled(self, mod: dict):
        # Refresh card fav star
        for card in self.mod_cards:
            if card.mod is mod:
                card.refresh_fav()

    def _on_order_changed(self):
        ordered_mods = [card.mod for card in self.mod_list.get_cards()]
        self.order_mgr.save_order(ordered_mods)

    def _on_toggle(self, mod: dict, enable: bool):
        folder: Path = mod["folder"]
        try:
            if enable:
                new_name = (folder.name[len(DISABLED_PREFIX):]
                            if folder.name.startswith(DISABLED_PREFIX) else folder.name)
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
            if self.details_panel.current_mod is mod:
                self.details_panel.show_mod(mod)
            self.status.showMessage(f"{'Enabled' if enable else 'Disabled'}: {mod['name']}")
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

    def _disable_all(self):
        for mod in self.mods:
            if mod["enabled"]:
                self._on_toggle(mod, False)

    def _update_stats(self):
        total    = len(self.mods)
        shown    = len(self.mod_cards)
        enabled  = sum(1 for m in self.mods if m["enabled"])
        disabled = total - enabled
        favs     = sum(1 for m in self.mods if self.favs.is_fav(mod_id(m)))
        green, red, yel = P["green"], P["red"], P["accent2"]
        self.count_label.setText(f"{total} mods")
        parts = [f"<span style='color:{green}'>{enabled} enabled</span>",
                 f"<span style='color:{red}'>{disabled} disabled</span>"]
        if favs:
            parts.append(f"<span style='color:{yel}'>{favs} ★</span>")
        if shown != total:
            parts.append(f"{shown} shown")
        self.stats_label.setText("  ·  ".join(parts))
        self.stats_label.setTextFormat(Qt.TextFormat.RichText)

    def _update_path_labels(self):
        self.mods_path_label.setText(f"Mods:\n{self.mods_dir or 'Not set'}")
        self.smapi_path_label.setText(f"SMAPI:\n{self.smapi_path or 'Not set'}")
        ok = bool(self.smapi_path and Path(self.smapi_path).exists())
        self.btn_launch.setEnabled(ok)

    # ── Profiles ──────────────────────────────────────────────────────────────

    def _current_enabled_ids(self) -> list[str]:
        return [mod_id(m) for m in self.mods if m["enabled"]]

    def _save_current_as_profile(self):
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.profiles.names():
            if QMessageBox.question(self, "Overwrite?",
                    f"'{name}' already exists. Overwrite?",
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
            profile_ids = set(self.profiles.get(signal))
            for mod in self.mods:
                want = mod_id(mod) in profile_ids
                if mod["enabled"] != want:
                    self._on_toggle(mod, want)
            self.status.showMessage(f"Applied profile: {signal}")

    # ── Log Viewer ────────────────────────────────────────────────────────────

    def _show_log(self):
        dlg = LogViewer(self)
        dlg.exec()

    # ── Paths Dialog ──────────────────────────────────────────────────────────

    def _show_paths_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Configure Paths")
        dlg.setMinimumWidth(560)
        dlg.setStyleSheet(self.styleSheet())
        vl = QVBoxLayout(dlg)
        vl.setSpacing(12)

        fs = (f"background:{P['surface2']}; border:1px solid {P['border']};"
              f"border-radius:4px; color:{P['text']}; padding:4px 8px;")
        bs = (f"QPushButton {{ background:{P['surface2']}; color:{P['text']};"
              f"border:1px solid {P['border']}; border-radius:4px; padding:4px 12px; }}"
              f"QPushButton:hover {{ border-color:{P['accent']}; }}")

        vl.addWidget(QLabel("Mods Directory:"))
        mods_row = QHBoxLayout()
        mods_edit = QLineEdit(str(self.mods_dir) if self.mods_dir else "")
        mods_edit.setStyleSheet(fs)
        mods_row.addWidget(mods_edit, 1)
        mb = QPushButton("Browse…")
        mb.setStyleSheet(bs)
        mb.clicked.connect(lambda: mods_edit.setText(
            QFileDialog.getExistingDirectory(dlg, "Select Mods Directory",
                str(self.mods_dir or Path.home())) or mods_edit.text()))
        mods_row.addWidget(mb)
        vl.addLayout(mods_row)

        vl.addWidget(QLabel("SMAPI Executable:"))
        smapi_row = QHBoxLayout()
        smapi_edit = QLineEdit(self.smapi_path or "")
        smapi_edit.setStyleSheet(fs)
        smapi_row.addWidget(smapi_edit, 1)
        sb = QPushButton("Browse…")
        sb.setStyleSheet(bs)
        sb.clicked.connect(lambda: smapi_edit.setText(
            QFileDialog.getOpenFileName(dlg, "Select SMAPI", str(Path.home()))[0]
            or smapi_edit.text()))
        smapi_row.addWidget(sb)
        vl.addLayout(smapi_row)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.setStyleSheet(f"QPushButton {{ background:{P['surface2']}; color:{P['text']};"
                         f"border:1px solid {P['border']}; border-radius:4px;"
                         f"padding:4px 16px; min-width:70px; }}"
                         f"QPushButton:hover {{ border-color:{P['accent']}; }}")
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
                QMessageBox.warning(self, "Invalid", f"Not found:\n{nm}")
            if ns and Path(ns).exists():
                self.smapi_path = ns; changed = True
            elif ns:
                QMessageBox.warning(self, "Invalid", f"Not found:\n{ns}")
            if changed:
                self._save_settings(); self.refresh_mods()

    # ── ZIP Install ───────────────────────────────────────────────────────────

    def _on_unzip(self, mod: dict):
        zip_path: Path = mod["zip_path"]
        msg = (f"Install '{mod['name']}' from:\n{zip_path.name}\n\n"
               "The ZIP will be extracted into your Mods folder and then deleted.")
        reply = QMessageBox.question(
            self, "Install Mod", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, result = install_zip_mod(zip_path, self.mods_dir)
        if success:
            QMessageBox.information(self, "Installed",
                f"'{mod['name']}' installed successfully as folder:\n{result}")
            self.refresh_mods()
        else:
            QMessageBox.critical(self, "Install Failed",
                f"Could not install '{mod['name']}':\n{result}")

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
        QMessageBox.critical(self, "Launch Failed", f"Could not start SMAPI:\n{msg}")
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
