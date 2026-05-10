
# 🌱 OD's Stardew Mod Manager
**Version 1.0** — Windows · macOS · Linux

A lightweight desktop mod manager for Stardew Valley. Enable and disable SMAPI mods,
organise them into profiles, and launch the game — all from one place.

---

## 📋 Requirements

- **Python 3.10 or newer**
- **PyQt6** (the GUI framework)
- **SMAPI** installed for Stardew Valley

Install PyQt6 by opening a terminal and running:

```
pip install PyQt6
```

> On Linux you may need to add `--break-system-packages` if pip warns you about it.

---

## 🚀 Installation

### Windows
1. Install Python from https://python.org (tick "Add Python to PATH" during install)
2. Open Command Prompt and run: `pip install PyQt6`
3. Place `sdv_mod_manager.py` and `icon.png` in the same folder anywhere you like
4. Double-click `sdv_mod_manager.py` to launch, or run: `python sdv_mod_manager.py`

### macOS
1. Install Python from https://python.org or via Homebrew: `brew install python`
2. Open Terminal and run: `pip3 install PyQt6`
3. Place `sdv_mod_manager.py` and `icon.png` in the same folder anywhere you like
4. Run from Terminal: `python3 sdv_mod_manager.py`

### Linux (Ubuntu / Kubuntu / Debian)
1. Open a terminal and run: `pip3 install PyQt6 --break-system-packages`
2. Place `sdv_mod_manager.py` and `icon.png` in a permanent folder, e.g.:
   ```
   ~/.local/share/sdv-mod-manager/
   ```
3. Run: `python3 sdv_mod_manager.py`

---

## ⚙️ First Launch — Setting Up Paths

On your first launch, you will need to specify where
your SMAPI "Mods" folder is. It's really easy to set
up with the built in settings menu.

First, click **⚙ Paths** in the toolbar and set:

| Field | What to point it at |
|-------|-------------------|
| Mods Directory | The `Mods` folder inside your Stardew Valley install |
| SMAPI Executable | The `StardewModdingAPI` binary (or `.exe` on Windows) |

### Common Mods folder locations

**Windows**
```
C:\Program Files (x86)\Steam\steamapps\common\Stardew Valley\Mods
C:\Program Files\Steam\steamapps\common\Stardew Valley\Mods
```

**macOS**
```
~/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/Mods
```

**Linux**
```
~/.local/share/Steam/steamapps/common/Stardew Valley/Mods
~/snap/steam/common/.local/share/Steam/steamapps/common/Stardew Valley/Mods
```

> Tip: You can confirm the exact path from SMAPI's own log output when it launches:
> `[SMAPI] Mods go here: ...`

---

## 🖥️ Enabling & Disabling Mods

Each mod appears as a card showing its name, author, version, and description.
Use the **checkbox** on the left of each card to toggle it on or off.

- 🟢 **Green dot** — mod is enabled, SMAPI will load it
- 🔴 **Red dot** — mod is disabled, SMAPI will skip it

**How it works under the hood:**
Disabling a mod adds a dot to the front of its folder name:
```
CJBCheats   →   .CJBCheats    (disabled)
.CJBCheats  →   CJBCheats     (re-enabled)
```
SMAPI natively skips any folder starting with a dot. **No files are ever deleted.**

---

## 🗂️ Profiles

Profiles let you save a named set of enabled mods and switch between them instantly —
useful for keeping a "Multiplayer" set separate from a "Solo" set, for example.

### Creating a profile
1. Enable/disable mods however you like
2. Click **💾 Save current as profile** in the sidebar
3. Type a name and confirm

### Applying a profile
Click **Apply** next to any profile. The app will enable every mod saved in that
profile and disable all others automatically.

### Profile options (⋮ menu)

| Option | What it does |
|--------|-------------|
| ✏ Rename | Give the profile a new name |
| 💾 Overwrite with current mods | Update the profile to match what's currently enabled |
| 🗑 Delete | Remove the profile (your mod files are not affected) |

### Where profiles are saved

| OS | Location |
|----|---------|
| Windows | `%APPDATA%\ODsStardewModManager\profiles.json` |
| macOS | `~/Library/Application Support/ODsStardewModManager/profiles.json` |
| Linux | `~/.config/ODsStardewModManager/profiles.json` |

---

## ▶️ Launching the Game

Click **▶ Launch with SMAPI** to start Stardew Valley.

The app will try to launch through **Steam** first (which keeps online multiplayer
working). If Steam isn't found it falls back to launching SMAPI directly.

**Linux users:** For multiplayer to work, make sure SMAPI is set as your Steam
launch option. In Steam, right-click Stardew Valley → Properties → General →
Launch Options and paste: (make sure to add the actual path)
```
"/path/to/StardewModdingAPI" %command%
```

---

## 📦 Building a Standalone Executable (No Python Required)

You can package the app into a single executable using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed sdv_mod_manager.py
```

The binary is created in the `dist/` folder next to your script.
Place `icon.png` in the same folder as the binary. You can put this
file anywhere

---

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| No mods appear | Click ⚙ Paths and verify the Mods Directory is set correctly |
| Mods still load after disabling | Wrong Mods path. Check SMAPI's log for the correct path |
| Launch button is greyed out | SMAPI path not configured. Set it in ⚙ Paths |
| Multiplayer doesn't work (Linux) | Set SMAPI as your Steam launch option (see above) |
| App won't start | Run `pip install PyQt6` (or `pip3 install PyQt6 --break-system-packages` on Linux) |
| Profiles not appearing | Check that the profiles.json file exists and contains valid JSON |
| Permission error when toggling | You don't have write access to the Mods folder. Check folder permissions |

---

## 🗑️ Uninstalling

Delete the `sdv_mod_manager.py` file (and the executable if you built one).

To also remove saved settings and profiles:

| OS | Path to delete |
|----|---------------|
| Windows | `%APPDATA%\ODsStardewModManager\` |
| macOS | `~/Library/Application Support/ODsStardewModManager/` |
| Linux | `~/.config/ODsStardewModManager/` |

Your mods are not affected — only the manager's own data is removed.

---

## 📄 Licence

Free to use and modify. Please credit **OD Mods** if you redistribute or build upon this.

---

*OD's Stardew Mod Manager v1.0 — made for the Stardew Valley community*
