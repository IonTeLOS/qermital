# Qermital

**Qermital** is a Qt-based terminal emulator that embeds `uxterm` process into a modern, feature-rich UI. It supports single-instance handling, system tray minimization, dual-pane layouts, custom fonts, and more.

---

## Features

- **Single-Instance Mode**  
  Allows only one primary instance. Additional launches trigger a new tab in the existing instance.

- **Dual-Pane Layout**  
  Optionally split the main window into two panes, each managing its own set of terminal tabs.

- **System Tray Support**  
  Minimize to the system tray; restore with a click.

- **Configurable Fonts & Colors**  
  Choose from built-in color themes and common monospace fonts.

- **Resizable Embedded Terminals**  
  Dynamically resizes `uxterm` based on the widget’s dimensions.

- **Custom Commands & Directories**  
  Automatically open new tabs in specified directories or run a startup command.

---

## Requirements

### 1. System Packages

Make sure the following **executables** and **libraries** are installed on your system:

- `xdotool`  
- `uxterm` usually part of `xterm`  
- `xrdb` (part of `x11-xserver-utils` on Debian/Ubuntu or `xorg-xrdb` on Arch)  
- `xdg-utils`  
- `libX11` & `libxcb`  

### 2. Python dependencies

All Python-related dependencies are listed in requirements.txt:

PySide6
qtawesome
qdarktheme
Install them via:

pip install -r requirements.txt
(If you’re running in a virtual environment, ensure it’s activated beforehand.)

## Installation

### Clone the Repository

```bash
git clone https://github.com/iontelos/qermital.git
cd qermital
pip install -r requirements.txt
python3 qermital.py

Usage
Argument	Description	Example
--new, -n	Force launch a new instance even if one is running.	qermital --new
--folder, -f	Initial directory for the terminal to open in.	qermital -f /home/user
--command, -c	Command to execute on startup.	qermital -c 'ls -la'
--tray, -t	Start the application minimized to the system tray.	qermital -t
--double, -d	Start the application with a dual-pane layout. (Works on initial launch or with --new.)	qermital -d
--max, -m	Start the application maximized.	qermital -m
```
### Fork and contribute

## Enjoy using Qermital!
