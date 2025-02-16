import sys
import subprocess
import os
import argparse
import json
import logging
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QFontComboBox,
    QSpinBox,
    QComboBox,
    QPushButton,
    QWidget,
    QFrame,
    QSizePolicy,
    QMenu,
    QTabWidget,
    QInputDialog,
    QMessageBox,
    QSplitter,
    QDialog,
    QLabel
)
from PySide6.QtCore import Qt, QProcess, QEvent, QTimer, QProcessEnvironment, QSize, QIODevice, Slot, QSettings
from PySide6.QtGui import QIcon, QCloseEvent, QAction, QFont, QPixmap, QPainter, QColor, QFontInfo, QFontDatabase
from PySide6.QtWidgets import QSystemTrayIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
import qtawesome as qta
import qdarktheme

# Configure logging at the beginning of the script
logging.basicConfig(level=logging.DEBUG, filename='qermital.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Define a unique server name for the single-instance mechanism
SERVER_NAME = "QermitalSingleInstanceServer"

DEFAULT_SETTINGS = {
    "font_family": "JetBrains Mono",
    "font_size": 14,
    "background_color": "#002b36",  # Solarized Dark Base03
    "foreground_color": "#839496"   # Solarized Dark Base0
}

# Define background color options: name -> hex code
BACKGROUND_COLORS = {
    "Solarized Dark": "#002b36",  # A well-regarded dark theme
    "Solarized Light": "#fdf6e3", # The light version for contrast
    "Dracula": "#282a36",         # Popular dark theme, good contrast
    "Nord": "#2e3440",            # Another popular dark blue theme
    "Monokai": "#272822",         # Dark theme with vibrant syntax highlighting
    "Black": "#000000",           # Pure black
    "Almost Black": "#080808",    # Slightly lighter black, less harsh
    "Dark Gray": "#333333",       # A standard dark gray
    "Medium Gray": "#808080",     # A neutral gray
    "Light Gray": "#cccccc",      # A light gray for specific use cases
    "White": "#ffffff",           # Pure white (often too bright for backgrounds)
    "Off White": "#f5f5f5",       # Softer white
    "Deep Blue": "#000080",       # Classic deep blue
    "Navy Blue": "#001f3f",       # Darker, richer blue
    "Dark Teal": "#008080",       # Dark greenish-blue
    "Forest Green": "#228b22",    # Dark green, earthy
    "Maroon": "#800000",          # Dark red, brownish
    "Olive": "#808000",           # Dark yellowish-green
    "Brown": "#a0522d",           # More standard brown than the original
    "Rosy Brown": "#bc8f8f",      # A softer, muted brown
    "Ubuntu Red": "#411824",      # Color of gnome-terminal
    "Girly Pink": "#fdd7e4"       # An attempt to create a cute background
}

# Define foreground color options: name -> hex code
FOREGROUND_COLORS = {
    "White": "#ffffff",
    "Off White": "#eee8d5",
    "Light Gray": "#d3d7cf",
    "Gray": "#93a1a1",
    "Solarized Yellow": "#b58900",
    "Solarized Cyan": "#2aa198",
    "Green": "#859900",
    "Bright Yellow": "#ffff00",
    "Retro Green": "#00ff00", # Classic bright green, like old monitors
    "Retro Blue": "#0000ff",  # Classic bright blue
    "Teal": "#008080",        # A nice in-between of blue and green, often seen in retro systems
    "Black": "#000000"
}

COMMON_MONOSPACE_FONTS = {  # Add common monospace fonts without "Mono"
    "Courier",
    "Courier New",
    "Fixed",
    "Fixedsys",
    "Consolas",
    "Source Code Pro",
    "Input",
    "Fira Code",
    "Roboto Mono",
    "PT Mono",
    "Anonymous Pro",
    "Inconsolata",
}

def get_monospace_fonts():
    """Retrieves monospace font families using QFontDatabase."""
    monospace_fonts = []
    for family in QFontDatabase.families():
        font = QFont(family)
        if font.exactMatch():
            info = QFontInfo(font)
            if info.fixedPitch():
                monospace_fonts.append(family)
    return monospace_fonts

def create_color_icon(color_hex, size=(16, 16)):
    """
    Create a QIcon with a colored square.

    Args:
        color_hex (str): Hexadecimal color code (e.g., "#ff0000").
        size (tuple): Size of the icon (width, height).

    Returns:
        QIcon: An icon filled with the specified color.
    """
    pixmap = QPixmap(*size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.NoPen)
    painter.drawRect(0, 0, size[0], size[1])
    painter.end()
    return QIcon(pixmap)

def check_executable_exists(executable_name):
    """
    Checks if an executable exists in the system's PATH.

    Args:
        executable_name: The name of the executable to check (e.g., "xdotool").

    Returns:
        True if the executable is found, False otherwise.
    """
    try:
        subprocess.run(['which', executable_name], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False

def merge_xresources():
    """
    Checks for xdotool and uxterm, shows QMessageBox and exits if not found.
    Checks if ~/.Xresources exists and creates it if it doesn't.
    Then merges ~/.Xresources using xrdb.
    In ~/.Xresources user can add their custom xterm configuration
    Raises an exception if xrdb command fails.
    """

    missing_executables = []
    if not check_executable_exists("xdotool"):
        missing_executables.append("xdotool")
    if not check_executable_exists("uxterm"):
        missing_executables.append("uxterm")
    if not check_executable_exists("xrdb"):
        missing_executables.append("xrdb")

    if missing_executables:
        app = QApplication.instance() # Get the existing QApplication instance or None
        if not app:
            app = QApplication(sys.argv) # Create a QApplication if it doesn't exist

        missing_list = ", ".join(missing_executables)
        error_message = f"Error: The following required executables are missing:\n\n{missing_list}\n\nPlease install them and try again."
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(error_message)
        msg_box.setWindowTitle("Missing Dependencies")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
        sys.exit(1) # Exit with a non-zero code to indicate an error

    xresources_path = Path.home() / '.Xresources'

    if not xresources_path.exists():
        print(f"~/.Xresources not found. Creating {xresources_path}")
        try:
            xresources_path.touch()
            print(f"Created empty {xresources_path}")
        except OSError as e:
            print(f"Error creating {xresources_path}: {e}")
            raise  # Re-raise the exception to stop execution if creation fails

    try:
        print(f"Merging {xresources_path} using xrdb...")
        subprocess.run(['xrdb', '-merge', str(xresources_path)], check=True, capture_output=True, text=True)
        print(f"{xresources_path} merged successfully.")
    except FileNotFoundError:
        print("Error: xrdb command not found. Is it installed?")
        raise  # Re-raise to indicate a critical issue if xrdb is required
    except subprocess.CalledProcessError as e:
        print(f"Error merging {xresources_path} with xrdb:")
        print(f"Return code: {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise

def create_qermital_desktop_entry():
    """
    Checks for ~/.local/share/applications/qermital.desktop.
    If not found, creates one with appropriate Exec and Icon paths,
    and registers it as an x-terminal-emulator.
    Copies qermital.png from MEIPASS to local icon directory.
    """

    desktop_entry_path = Path.home() / '.local/share/applications/qermital.desktop'
    icon_filename = 'qermital.png'
    local_icon_dir = Path.home() / '.local/share/icons/hicolor/scalable/apps'
    local_icon_path = local_icon_dir / icon_filename
    exec_command = Path.home() / '.local/bin/qermital'

    print(f"Checking for desktop entry: {desktop_entry_path}")

    if not desktop_entry_path.exists():
        print(f"Desktop entry not found. Creating {desktop_entry_path}")

        # Ensure ~/.local/share/applications directory exists
        desktop_entry_dir = desktop_entry_path.parent
        desktop_entry_dir.mkdir(parents=True, exist_ok=True)

        # Ensure local icon directory exists
        local_icon_dir.mkdir(parents=True, exist_ok=True)

        # Find icon source path in MEIPASS or fallback to current directory
        if hasattr(sys, '_MEIPASS'):
            icon_source_dir = Path(sys._MEIPASS)
        else:
            icon_source_dir = Path('.') # Fallback to current directory when not in onefile
        icon_source_path = icon_source_dir / icon_filename

        if not icon_source_path.exists():
            print(f"Warning: Icon file '{icon_filename}' not found at source: {icon_source_path}")
            print("Make sure qermital.png is included in your PyInstaller data files or in the current directory for development.")
            default_icon_path = "/usr/share/icons/hicolor/scalable/apps/python3.png" # Example fallback icon - adjust as needed or set to None
            if default_icon_path and Path(default_icon_path).exists():
                print(f"Using default icon instead: {default_icon_path}")
                icon_to_use = default_icon_path
            else:
                icon_to_use = None # No icon
        else:
            try:
                print(f"Copying icon from {icon_source_path} to {local_icon_path}")
                shutil.copy2(str(icon_source_path), str(local_icon_path)) # copy2 preserves metadata
                icon_to_use = str(local_icon_path)
                print(f"Icon copied successfully to {local_icon_path}")
            except Exception as e:
                print(f"Error copying icon: {e}")
                icon_to_use = None # No icon if copy fails

        # Construct .desktop file content with MimeType for x-terminal-emulator
        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Qermital
Comment=Qt Terminal Emulator
Exec={exec_command}
Icon={'qermital' if icon_to_use else 'terminal'}
Terminal=false
Categories=System;TerminalEmulator;
StartupWMClass=Qermital
MimeType=application/x-terminal-emulator;
"""
        if icon_to_use:
            # If icon was copied, use the full path in the Icon line.
            # Otherwise 'qermital' will try to find icon in icon themes if available.
            desktop_content = desktop_content.replace("Icon=qermital", f"Icon={icon_to_use}")


        try:
            with open(desktop_entry_path, 'w') as desktop_file:
                desktop_file.write(desktop_content)
            print(f"Desktop entry created at {desktop_entry_path}")

            # Make the .desktop file executable (though not strictly necessary for .desktop files)
            os.chmod(desktop_entry_path, 0o755) # rwxr-xr-x permissions
            print(f"Desktop entry made executable.")

        except Exception as e:
            print(f"Error creating desktop entry: {e}")
    else:
        print(f"Desktop entry already exists at {desktop_entry_path}")


class SettingsDialog(QDialog):
    """Dialog for configuring terminal settings."""

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.settings = settings or DEFAULT_SETTINGS.copy()
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog's UI components."""
        layout = QVBoxLayout()

        # Font Selection
        font_layout = QHBoxLayout()
        font_label = QLabel("Font:")
        self.font_combo = QFontComboBox()

        # Filter to show only monospace fonts
        monospace_fonts = get_monospace_fonts()
        if monospace_fonts:
            self.font_combo.setCurrentFont(QFont(monospace_fonts[0]))
            self.font_combo.setFontFilters(QFontComboBox.MonospacedFonts)
        else:
            self.font_combo.addItem("No monospace fonts found.")
            self.font_combo.setEnabled(False)

        # Set the current font if it's available in monospace_fonts
        current_font = self.settings.get("font_family", DEFAULT_SETTINGS["font_family"])
        if current_font in monospace_fonts:
            self.font_combo.setCurrentFont(QFont(current_font))
        else:
            # Fallback to a default monospace font
            fallback_font = monospace_fonts[0] if monospace_fonts else "Courier New"
            self.font_combo.setCurrentFont(QFont(fallback_font))
            self.settings["font_family"] = fallback_font  # Update settings to fallback

        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_combo)
        layout.addLayout(font_layout)

        # Font Size Selection
        size_layout = QHBoxLayout()
        size_label = QLabel("Font Size:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 22)
        self.size_spin.setValue(self.settings["font_size"])
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        layout.addLayout(size_layout)

        # Background Color Selection
        bg_layout = QHBoxLayout()
        bg_label = QLabel("Background Color:")
        self.bg_combo = QComboBox()
        for name, hex_code in BACKGROUND_COLORS.items():
            icon = create_color_icon(hex_code)
            self.bg_combo.addItem(icon, name)
        # Set the current index based on the saved setting
        current_bg = self.get_color_name(BACKGROUND_COLORS, self.settings["background_color"])
        bg_index = self.bg_combo.findText(current_bg)
        if bg_index != -1:
            self.bg_combo.setCurrentIndex(bg_index)
        bg_layout.addWidget(bg_label)
        bg_layout.addWidget(self.bg_combo)
        layout.addLayout(bg_layout)

        # Foreground Color Selection
        fg_layout = QHBoxLayout()
        fg_label = QLabel("Foreground Color:")
        self.fg_combo = QComboBox()
        for name, hex_code in FOREGROUND_COLORS.items():
            icon = create_color_icon(hex_code)
            self.fg_combo.addItem(icon, name)
        # Set the current index based on the saved setting
        current_fg = self.get_color_name(FOREGROUND_COLORS, self.settings["foreground_color"])
        fg_index = self.fg_combo.findText(current_fg)
        if fg_index != -1:
            self.fg_combo.setCurrentIndex(fg_index)
        fg_layout.addWidget(fg_label)
        fg_layout.addWidget(self.fg_combo)
        layout.addLayout(fg_layout)

        # Font Preview
        preview_layout = QHBoxLayout()
        preview_label = QLabel("Preview:")
        self.font_preview = QLabel("Sample Text")
        self.font_preview.setFont(QFont(self.settings["font_family"], self.settings["font_size"]))
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.font_preview)
        layout.addLayout(preview_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Defaults")
        revert_button = QPushButton("Revert to Defaults")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(save_button)
        button_layout.addWidget(revert_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect buttons
        save_button.clicked.connect(self.save_settings)
        revert_button.clicked.connect(self.revert_to_defaults)
        cancel_button.clicked.connect(self.reject)

        # Connect signals for live preview
        self.font_combo.currentFontChanged.connect(self.update_font_preview)
        self.size_spin.valueChanged.connect(self.update_font_preview)

    def get_color_name(self, color_dict, hex_code):
        """Retrieve the color name based on the hex code."""
        for name, code in color_dict.items():
            if code.lower() == hex_code.lower():
                return name
        return ""

    def save_settings(self):
        """Save the selected settings and accept the dialog."""
        self.settings["font_family"] = self.font_combo.currentFont().family()
        self.settings["font_size"] = self.size_spin.value()
        # Get the hex codes based on selected color names
        bg_name = self.bg_combo.currentText()
        fg_name = self.fg_combo.currentText()
        self.settings["background_color"] = BACKGROUND_COLORS.get(bg_name, DEFAULT_SETTINGS["background_color"])
        self.settings["foreground_color"] = FOREGROUND_COLORS.get(fg_name, DEFAULT_SETTINGS["foreground_color"])
        self.accept()

    def revert_to_defaults(self):
        """Revert settings to default values and update the UI."""
        self.settings = DEFAULT_SETTINGS.copy()
        self.font_combo.setCurrentFont(QFont(self.settings["font_family"]))
        self.size_spin.setValue(self.settings["font_size"])

        # Set Background Color
        bg_name = self.get_color_name(BACKGROUND_COLORS, self.settings["background_color"])
        bg_index = self.bg_combo.findText(bg_name)
        if bg_index != -1:
            self.bg_combo.setCurrentIndex(bg_index)

        # Set Foreground Color
        fg_name = self.get_color_name(FOREGROUND_COLORS, self.settings["foreground_color"])
        fg_index = self.fg_combo.findText(fg_name)
        if fg_index != -1:
            self.fg_combo.setCurrentIndex(fg_index)

        # Update Font Preview
        self.update_font_preview(self.font_combo.currentFont())

        self.accept()

    def get_settings(self):
        """Return the updated settings."""
        return self.settings

    def update_font_preview(self, font):
        """Update the font preview based on the selected font and size."""
        if isinstance(font, QFont):
            current_size = self.size_spin.value()
            self.font_preview.setFont(QFont(font.family(), current_size))
        else:
            logging.warning("Received unexpected font type for preview update.")

class XTermWidget(QFrame):
    """Embeddable widget that embeds a uxterm terminal."""

    def __init__(self, initial_directory=None, command=None, parent=None):
        super().__init__(parent)
        self.initial_directory = initial_directory or os.getcwd()
        self.command = command
        self.current_settings = DEFAULT_SETTINGS.copy()
        self.setup_ui()
        self.start_uxterm()

    def setup_ui(self):
        """Initialize the widget UI properties."""
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create resize timer
        self.resize_timer = QTimer(self)
        self.resize_timer.timeout.connect(self.resize_terminal)
        self.resize_timer.setSingleShot(True)

        # Install event filter for resize events
        self.installEventFilter(self)

    def start_uxterm(self):
        """Start and embed uxterm process."""
        try:
            # Explicitly load .Xresources
            merge_xresources()
            logging.debug("Loaded .Xresources successfully.")

            # Set up environment
            env = QProcessEnvironment.systemEnvironment()
            env.insert("WINDOWID", str(int(self.winId())))
            env.insert("RESOURCE_MANAGER", str(Path.home() / '.Xresources'))
            env.insert("LANG", "en_US.UTF-8")  # Ensure UTF-8 support
            env.insert("TERM", "xterm-256color")  # Ensure TERM supports 256 colors
            self.process = QProcess(self)
            self.process.setProcessEnvironment(env)
            self.process.setWorkingDirectory(self.initial_directory)

            # Configure uxterm parameters based on current_settings
            font_family = self.current_settings.get("font_family", "JetBrains Mono")
            font_size = self.current_settings.get("font_size", 14)
            bg_color = self.current_settings.get("background_color", "#002b36")
            fg_color = self.current_settings.get("foreground_color", "#839496")

            if self.command:
                bash_command = f'cd "{self.initial_directory}"; {self.command}; exec bash'
            else:
                bash_command = f'cd "{self.initial_directory}"; exec bash'

            # Base uxterm command
            uxterm_command = [
                'uxterm',
                '-fa', font_family,
                '-fs', str(font_size),
                '-bg', bg_color,
                '-fg', fg_color,
                '-cr', fg_color,     # Cursor color same as foreground
                '-bc',               # Enable bold colors
                '+sb',               # Disable scrollbar
                '-class', 'UXTerm',  # Ensure class is UXTerm
                '-into', str(int(self.winId())),
                '-e', 'bash', '-c', bash_command
            ]

            # Debug: Print the uxterm command for verification
            logging.debug("Launching uxterm with the following command:")
            logging.debug(' '.join(uxterm_command))
            print("Launching uxterm with the following command:")
            print(' '.join(uxterm_command))

            # Start uxterm
            self.process.start(uxterm_command[0], uxterm_command[1:])  # Pass all arguments after 'uxterm'

            # Check if process started successfully
            if not self.process.waitForStarted(3000):
                raise RuntimeError("uxterm failed to start.")

            logging.debug("uxterm started successfully.")
            # Initial resize after a short delay
            QTimer.singleShot(100, self.resize_terminal)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to load .Xresources: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load .Xresources: {e}")
        except Exception as e:
            logging.error(f"Failed to start uxterm: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start uxterm: {e}")

    def apply_settings(self, settings):
        """Apply new settings to the terminal widget."""
        self.current_settings = settings.copy()
        self.restart_uxterm()

    def restart_uxterm(self):
        """Restart the uxterm process to apply new settings."""
        self.terminate()
        self.start_uxterm()

    def terminate(self):
        """Clean up the uxterm process."""
        if hasattr(self, 'process') and self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                self.process.kill()
            logging.debug("uxterm process terminated.")

    def resize_terminal(self):
        """Resize the terminal to match widget size."""
        try:
            pid = self.process.processId()
            if pid:
                # Find uxterm windows for this process
                cmd = f"xdotool search --pid {pid} --class UXTerm"
                result = subprocess.check_output(cmd, shell=True).decode().strip()

                if result:
                    window_ids = result.split('\n')
                    size = self.size()

                    for window_id in window_ids:
                        # Resize window
                        resize_cmd = f"xdotool windowsize {window_id} {size.width()} {size.height()}"
                        subprocess.run(resize_cmd, shell=True, check=True)

                        # Update terminal dimensions
                        char_width = 7  # Adjust these values based on your terminal font
                        char_height = 15
                        cols = max(1, int(size.width() / char_width))
                        rows = max(1, int(size.height() / char_height))

                        # Get the TTY of the uxterm process directly
                        tty_cmd = f"ps -o tty= -p {pid}"
                        tty_output = subprocess.check_output(tty_cmd, shell=True).decode().strip()
                        if tty_output and tty_output != "?":  # Ensure valid TTY output
                            pty_device = f"/dev/{tty_output}"
                            stty_cmd = f"stty -F {pty_device} rows {rows} columns {cols}"
                            subprocess.run(stty_cmd, shell=True, check=True)

        except subprocess.CalledProcessError as e:

            QMessageBox.warning(self, "Resize Warning", f"Error resizing terminal: {e}")
        except Exception as e:

            QMessageBox.warning(self, "Resize Warning", f"Unexpected error: {e}")


    def eventFilter(self, obj, event):
        """Handle resize events."""
        if obj == self and event.type() == QEvent.Resize:
            self.resize_timer.start(50)  # Debounce resize events
        return super().eventFilter(obj, event)

    def closeEvent(self, event: QCloseEvent):
        """Ensure the uxterm process is terminated on widget close."""
        self.terminate()
        event.accept()


class TerminalEmulator(QMainWindow):
    """Main application window that manages multiple terminal tabs."""

    def __init__(self, initial_directory=None, command=None, start_minimized=False, start_double_pane=False, start_maximized=False):
        super().__init__()
        self.initial_directory = initial_directory or os.getcwd()
        self.command = command  # Store the user-specified command
        self.start_minimized = start_minimized
        self.start_double_pane = start_double_pane
        self.start_maximized = start_maximized
        self.tab_counter = 0  # Add counter for tab naming
        self.command_executed = False  # Flag to ensure command executes only once
        self.second_tab_widget = None  # Initialize second_tab_widget as None

        # Load settings
        self.load_settings()

        self.initUI()
        self.init_tray()
        if self.start_minimized:
            self.hide()
            self.tray_icon.showMessage(
                "Qermital",
                "Application started minimized to tray.",
                QSystemTrayIcon.Information,
                2000
            )
        if self.start_double_pane:
            # Initialize both panes with at least one tab each
            QTimer.singleShot(500, self.initialize_double_pane)
        if self.start_maximized:
            self.showMaximized()

    def load_settings(self):
        """Load settings from QSettings or use defaults."""
        self.settings = DEFAULT_SETTINGS.copy()
        qsettings = QSettings("Qermital", "TerminalEmulator")
        self.settings["font_family"] = qsettings.value("font_family", DEFAULT_SETTINGS["font_family"])
        self.settings["font_size"] = int(qsettings.value("font_size", DEFAULT_SETTINGS["font_size"]))
        self.settings["background_color"] = qsettings.value("background_color", DEFAULT_SETTINGS["background_color"])
        self.settings["foreground_color"] = qsettings.value("foreground_color", DEFAULT_SETTINGS["foreground_color"])

    def save_settings(self):
        """Save current settings to QSettings."""
        qsettings = QSettings("Qermital", "TerminalEmulator")
        qsettings.setValue("font_family", self.settings["font_family"])
        qsettings.setValue("font_size", self.settings["font_size"])
        qsettings.setValue("background_color", self.settings["background_color"])
        qsettings.setValue("foreground_color", self.settings["foreground_color"])

    def initUI(self):
        """Initialize the main UI."""
        self.setWindowTitle('Qermital')

        # Set window icon
        icon_path = self.get_resource_path("qermital.png")
        self.setWindowIcon(QIcon(icon_path))

        self.resize(1200, 800)

        # Create a splitter to manage panes, non-adjustable
        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)

        # Main Tab Widget
        self.main_tab_widget = QTabWidget()
        self.main_tab_widget.setMovable(True)  # Make tabs movable
        self.main_tab_widget.setTabsClosable(True)
        self.main_tab_widget.tabCloseRequested.connect(self.close_main_tab)

        # Make tabs scrollable
        self.main_tab_widget.setTabBarAutoHide(False)
        self.main_tab_widget.setUsesScrollButtons(True)
        self.main_tab_widget.setElideMode(Qt.ElideRight)

        # Set minimum width to prevent shrinking
        self.main_tab_widget.setMinimumWidth(400)

        self.splitter.addWidget(self.main_tab_widget)

        # Add initial terminal tab
        self.add_terminal_tab()  # First tab with command (if provided)

        # Context menu for tabs
        self.main_tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.main_tab_widget.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, self.main_tab_widget)
        )

    def show_context_menu(self, position, tab_widget):
        """Show context menu for the specified tab widget."""
        context_menu = QMenu()

        current_index = tab_widget.currentIndex()
        if current_index == -1:
            return  # No tab to act upon

        # Add "Add Tab" action
        add_tab_icon = qta.icon('mdi.plus', color='blue', icon_size=(32, 32))
        add_tab_action = QAction(add_tab_icon, "Add Tab", self)
        add_tab_action.triggered.connect(
            lambda: self.add_terminal_tab(
                pane='main' if tab_widget == self.main_tab_widget else 'second'
            )
        )
        context_menu.addAction(add_tab_action)

        # Add "Open Duality" action only for main_tab_widget
        if tab_widget == self.main_tab_widget and not self.second_tab_widget:
            open_half_icon = qta.icon('mdi.arrow-split-vertical', color='blue', icon_size=(32, 32))
            open_half_action = QAction(open_half_icon, "Open Dual Pane", self)
            open_half_action.triggered.connect(self.initialize_double_pane)
            context_menu.addAction(open_half_action)

        # Add "Move Tab to Second Pane" action
        move_tab_icon = qta.icon('mdi.arrow-right-bold-circle-outline', color='blue', icon_size=(32, 32))  # Choose an appropriate icon
        move_tab_action = QAction(move_tab_icon, "Move Tab to Second Pane", self)
        move_tab_action.triggered.connect(lambda: self.move_tab_to_second_pane(tab_widget, current_index))
        context_menu.addAction(move_tab_action)

        # Add "Close Second Pane" action if splitter has two panes
        if self.second_tab_widget:
            close_half_icon = qta.icon('mdi.window-close', color='blue', icon_size=(32, 32))
            close_half_action = QAction(close_half_icon, "Close Second Pane", self)
            close_half_action.triggered.connect(self.close_second_half)
            context_menu.addAction(close_half_action)

        # Add "Rename Tab" action
        rename_tab_icon = qta.icon('mdi.rename-box', color='blue', icon_size=(32, 32))
        rename_tab_action = QAction(rename_tab_icon, "Rename Tab", self)
        rename_tab_action.triggered.connect(
            lambda: self.rename_tab(tab_widget, current_index)
        )
        context_menu.addAction(rename_tab_action)

        # Add "Toggle Tabbar" action
        toggle_tabbar_icon = qta.icon('mdi.toggle-switch', color='blue', icon_size=(32, 32))
        toggle_tabbar_action = QAction(toggle_tabbar_icon, "Toggle Bar", self)
        toggle_tabbar_action.triggered.connect(
            lambda: self.toggle_tab_bar()
        )
        context_menu.addAction(toggle_tabbar_action)

        context_menu.addSeparator()

        # Add "Settings" action
        settings_icon = qta.icon('mdi.settings-helper', color='blue', icon_size=(32, 32))
        settings_action = QAction(settings_icon, "Settings", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        context_menu.addAction(settings_action)

        # Add "Minimize to Tray" action
        minimize_tray_icon = qta.icon('mdi.window-minimize', color='blue', icon_size=(32, 32))
        minimize_tray_action = QAction(minimize_tray_icon, "Minimize to Tray", self)
        minimize_tray_action.triggered.connect(self.hide)
        context_menu.addAction(minimize_tray_action)

        # Add "Exit App" action
        exit_app_icon = qta.icon('mdi.exit-to-app', color='blue', icon_size=(32, 32))
        exit_app_action = QAction(exit_app_icon, "Exit App", self)
        exit_app_action.triggered.connect(QApplication.instance().quit)
        context_menu.addAction(exit_app_action)

        # Display the context menu at the cursor position
        context_menu.exec(tab_widget.mapToGlobal(position))

    def open_settings_dialog(self):
        """Open the Settings Dialog."""
        dialog = SettingsDialog(self, settings=self.settings.copy())
        if dialog.exec() == QDialog.Accepted:
            # Update settings with user selections
            self.settings = dialog.get_settings()
            self.save_settings()
            logging.debug("Settings updated and saved.")

            # Apply settings to existing terminal widgets
            for index in range(self.main_tab_widget.count()):
                tab = self.main_tab_widget.widget(index)
                if isinstance(tab, XTermWidget):
                    tab.apply_settings(self.settings)

            if self.second_tab_widget:
                for index in range(self.second_tab_widget.count()):
                    tab = self.second_tab_widget.widget(index)
                    if isinstance(tab, XTermWidget):
                        tab.apply_settings(self.settings)

    def get_resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller."""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = Path(__file__).parent
        return os.path.join(base_path, relative_path)

    def init_tray(self):
        """Initialize the system tray icon and its menu."""
        # Set up system tray icon
        icon_path = self.get_resource_path("qermital.png")
        self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
        self.tray_icon.setToolTip("Qermital Terminal Emulator")

        # Create tray context menu
        tray_menu = QMenu()

        # Restore Action
        restore_icon = qta.icon('mdi.home', color='blue', icon_size=(32, 32))  # Using mdi.home as an example
        restore_action = QAction(restore_icon, "Restore", self)
        restore_action.triggered.connect(self.show_normal)
        tray_menu.addAction(restore_action)

        # Minimize Action
        minimize_icon = qta.icon('mdi.window-minimize', color='blue', icon_size=(32, 32))
        minimize_action = QAction(minimize_icon, "Minimize to Tray", self)
        minimize_action.triggered.connect(self.hide)
        tray_menu.addAction(minimize_action)

        # Settings Action
        settings_icon = qta.icon('mdi.cog', color='blue', icon_size=(32, 32))
        settings_action = QAction(settings_icon, "Settings", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        tray_menu.addAction(settings_action)

        # About Action
        about_icon = qta.icon('mdi.information', color='blue', icon_size=(32, 32))
        about_action = QAction(about_icon, "About", self)
        about_action.triggered.connect(self.open_about_dialog)
        tray_menu.addAction(about_action)

        # Exit Action
        exit_icon = qta.icon('mdi.exit-to-app', color='blue', icon_size=(32, 32))
        exit_action = QAction(exit_icon, "Exit App", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # Double click to restore
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        self.tray_icon.show()

    def toggle_tab_bar(self):
        # Toggle visibility of the tab bar
        is_visible = self.main_tab_widget.tabBar().isVisible()
        self.main_tab_widget.tabBar().setVisible(not is_visible)
        if self.second_tab_widget:
            self.second_tab_widget.tabBar().setVisible(not is_visible)


    def open_about_dialog(self):
        try:
            dialog = AboutDialog(None)  # Pass None as parent to avoid TypeError
            dialog.exec()
        except TypeError as e:
            QMessageBox.critical(
                None,
                "Error Opening About Dialog",
                f"An error occurred while opening the About dialog:\n{e}"
            )

    def on_tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.Trigger:
            self.show_normal()

    def show_normal(self):
        """Restore the window from the tray and bring it to the front."""
        self.show()
        self.raise_()
        self.activateWindow()
        # Additional steps to ensure the window is on top
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def add_terminal_tab(self, directory=None, command=None, pane='main'):
        """Add a new terminal tab to the specified pane."""
        directory = directory or self.initial_directory

        # Determine if the command should be executed on this tab
        if pane == 'main':
            execute_command = not self.command_executed and self.command
            if execute_command:
                cmd = self.command
                self.command_executed = True  # Ensure command is only executed once
            else:
                cmd = command  # Use the command passed from the message
        elif pane == 'second':
            # In second pane, do not execute the initial command unless specified
            cmd = command
        else:
            # Default to main pane if invalid pane specified
            pane = 'main'
            execute_command = not self.command_executed and self.command
            if execute_command:
                cmd = self.command
                self.command_executed = True
            else:
                cmd = command

        self.tab_counter += 1  # Increment counter
        terminal_widget = XTermWidget(initial_directory=directory, command=cmd, parent=self)
        terminal_widget.apply_settings(self.settings)  # Apply current settings to the new tab

        tab_label = f"Terminal {self.tab_counter}"
        if pane == 'main':
            self.main_tab_widget.addTab(terminal_widget, tab_label)
            self.main_tab_widget.setCurrentWidget(terminal_widget)
        elif pane == 'second' and self.second_tab_widget:
            self.second_tab_widget.addTab(terminal_widget, tab_label)
            self.second_tab_widget.setCurrentWidget(terminal_widget)

        # Bring the window to front after adding a new tab
        self.show_normal()

    def initialize_double_pane(self):
        """Initialize both panes with at least one tab each."""
        # Ensure main pane has at least one tab
        if self.main_tab_widget.count() == 0:
            self.add_terminal_tab(pane='main')

        # Create second pane and add a tab to it
        if not self.second_tab_widget:
            self.create_second_pane()
            self.add_terminal_tab(pane='second')

    def close_main_tab(self, index):
        """Close the specified tab in the main pane."""
        tab = self.main_tab_widget.widget(index)
        if isinstance(tab, XTermWidget):
            tab.terminate()
        self.main_tab_widget.removeTab(index)

        if self.main_tab_widget.count() == 0:
            self.tab_counter = 0  # Reset counter when all tabs are closed
            self.command_executed = False  # Reset command execution flag
            self.add_terminal_tab()

    def move_tab_to_second_pane(self, tab_widget, index):
        """Move the selected tab from the main pane to the second pane."""
        if tab_widget != self.main_tab_widget:
            QMessageBox.warning(self, "Move Tab", "Only tabs from the main pane can be moved to the second pane.")
            return

        tab = tab_widget.widget(index)
        if isinstance(tab, XTermWidget):
            tab_label = tab_widget.tabText(index)
            tab_widget.removeTab(index)

            # Ensure the second pane exists
            if not self.second_tab_widget:
                self.create_second_pane()

            # Move the tab to the second pane
            self.second_tab_widget.addTab(tab, tab_label)
            self.second_tab_widget.setCurrentWidget(tab)

            if self.main_tab_widget.count() == 0:
                self.add_terminal_tab(pane='main')

    def create_second_pane(self):
        """Create the second pane and set up its properties."""
        self.second_tab_widget = QTabWidget()
        self.second_tab_widget.setMovable(True)
        self.second_tab_widget.setTabsClosable(True)
        self.second_tab_widget.tabCloseRequested.connect(self.close_second_tab)
        self.second_tab_widget.setTabBarAutoHide(False)
        self.second_tab_widget.setUsesScrollButtons(True)
        self.second_tab_widget.setElideMode(Qt.ElideRight)
        self.second_tab_widget.setMinimumWidth(300)  # Prevent shrinking

        # Add second_tab_widget to splitter
        self.splitter.addWidget(self.second_tab_widget)

        # Always divide window in half
        total_width = self.splitter.size().width()
        half_width = total_width // 2
        self.splitter.setSizes([half_width, half_width])

        # Disable splitter handle to prevent user resizing
        if self.splitter.count() > 1:
            self.splitter.handle(1).setEnabled(False)

        # Update context menus for the second_tab_widget
        self.second_tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.second_tab_widget.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, self.second_tab_widget)
        )

    def close_second_half(self):
        """Close the second half and expand the main tab widget to occupy the full width."""
        if not self.second_tab_widget:
            QMessageBox.information(self, "Info", "Second pane is already closed.")
            return

        # Move all tabs from the second_tab_widget back to the main_tab_widget
        while self.second_tab_widget.count() > 0:
            tab_widget = self.second_tab_widget.widget(0)
            tab_label = self.second_tab_widget.tabText(0)
            self.second_tab_widget.removeTab(0)
            self.main_tab_widget.addTab(tab_widget, tab_label)
            self.main_tab_widget.setCurrentWidget(tab_widget)

        # Remove the second_tab_widget from the splitter
        second_pane = self.splitter.widget(1)
        if second_pane:
            second_pane.setParent(None)
            self.second_tab_widget.deleteLater()
            self.second_tab_widget = None

        # Expand the main_tab_widget to occupy the full width
        self.splitter.setSizes([self.splitter.size().width(), 0])


    def close_second_tab(self, index):
        """Close a tab in the second_tab_widget."""
        if not self.second_tab_widget:
            QMessageBox.information(self, "Info", "No tabs to close in the second pane.")
            return

        tab_widget = self.second_tab_widget.widget(index)
        if isinstance(tab_widget, XTermWidget):
            tab_widget.terminate()
        self.second_tab_widget.removeTab(index)

        # If second_tab_widget has no more tabs, remove it
        if self.second_tab_widget.count() == 0:
            second_pane = self.splitter.widget(1)
            if second_pane:
                second_pane.setParent(None)
                self.second_tab_widget.deleteLater()
                self.second_tab_widget = None

                # Re-enable splitter handle
                if self.splitter.count() > 1:
                    self.splitter.handle(1).setEnabled(True)

    def close_tab(self, tab_widget, index):
        """Close the specified tab in the given tab widget."""
        if isinstance(tab_widget, QTabWidget):
            tab = tab_widget.widget(index)
            if isinstance(tab, XTermWidget):
                tab.terminate()
            tab_widget.removeTab(index)

            # If main_tab_widget has no more tabs, reset counter and add a new tab
            if tab_widget == self.main_tab_widget and tab_widget.count() == 0:
                self.tab_counter = 0  # Reset counter when all tabs are closed
                self.command_executed = False  # Reset command execution flag
                self.add_terminal_tab()
            elif tab_widget == self.second_tab_widget and tab_widget.count() == 0:
                # If second_tab_widget has no more tabs, remove it
                second_pane = self.splitter.widget(1)
                if second_pane:
                    second_pane.setParent(None)
                    self.second_tab_widget.deleteLater()
                    self.second_tab_widget = None

                    # Re-enable splitter handle
                    if self.splitter.count() > 1:
                        self.splitter.handle(1).setEnabled(True)

    def rename_tab(self, tab_widget, index):
        """Rename the specified tab in the given tab widget."""
        if isinstance(tab_widget, QTabWidget):
            current_tab_text = tab_widget.tabText(index)
            new_tab_text, ok = QInputDialog.getText(
                self,
                "Rename Tab",
                "Enter new tab name:",
                text=current_tab_text
            )
            if ok and new_tab_text:
                tab_widget.setTabText(index, new_tab_text)

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        reply = QMessageBox.question(
            self,
            'Quit Qermital',
            "Are you sure you want to quit Qermital?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Terminate all terminal processes in main_tab_widget
            for index in range(self.main_tab_widget.count()):
                tab = self.main_tab_widget.widget(index)
                if isinstance(tab, XTermWidget):
                    tab.terminate()
            # Terminate all terminal processes in second_tab_widget
            if self.second_tab_widget:
                for index in range(self.second_tab_widget.count()):
                    tab = self.second_tab_widget.widget(index)
                    if isinstance(tab, XTermWidget):
                        tab.terminate()
            self.tray_icon.hide()
            event.accept()
            QApplication.quit()
        else:
            event.ignore()

    def handle_new_instance_message(self, message):
        """Handle incoming messages from new instances."""
        try:
            data = json.loads(message)
            action = data.get('action')
            folder = data.get('folder', None)
            command = data.get('command', None)

            if action == 'open_new_tab':
                if folder and os.path.isdir(folder):
                    self.add_terminal_tab(directory=folder, command=command)
                else:
                    self.add_terminal_tab(command=command)

                # Bring the window to front
                self.show_normal()
        except json.JSONDecodeError:
            # If message is not JSON, default behavior
            self.add_terminal_tab()
            self.show_normal()


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set window title
        self.setWindowTitle("About")

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        # Set minimum size
        self.setMinimumSize(300, 200)

        # Initialize layout
        self.layout = QVBoxLayout()

        # Create a QLabel with HTML content to include clickable links
        info_label = QLabel(
            "<h2>Qermital</h2>"
            "<p>Version 1.0</p>"
            "<p>Terminal Emulator using (u)xterm.</p>"
            '<p>GitHub Repository: <a href="https://github.com/iontelos/qermital">https://github.com/iontelos/qermital</a></p>'
        )
        info_label.setOpenExternalLinks(True)  # Enable clickable links
        info_label.setWordWrap(True)  # Enable word wrapping
        self.layout.addWidget(info_label)

        # Set the layout for the dialog
        self.setLayout(self.layout)

    def focusOutEvent(self, event):
        """
        Override the focusOutEvent to ensure the dialog closes when it loses focus.
        This is an additional safety measure; Qt.Popup should handle this automatically.
        """
        self.close()
        super().focusOutEvent(event)


class SingleInstanceApplication(QApplication):
    """A QApplication subclass that ensures only a single instance runs."""

    def __init__(self, argv, args):
        super().__init__(argv)
        self.server = None
        self.socket = None
        self.main_window = None
        self.args = args

        # Attempt to create a QLocalServer
        self.server = QLocalServer()
        if self.server.listen(SERVER_NAME):
            # No existing instance is running; this instance is the primary
            self.server.newConnection.connect(self.receive_message)
            logging.debug("No existing instance detected. Running as primary instance.")
        else:
            # An existing instance is running; send a message to it
            logging.debug("Another instance detected. Sending message to open a new tab.")
            self.send_message()
            sys.exit(0)  # Exit the new instance

    def send_message(self):
        """Send a message to the primary instance to open a new tab."""
        socket = QLocalSocket()
        socket.connectToServer(SERVER_NAME)
        if not socket.waitForConnected(1000):
            QMessageBox.warning(None, "Qermital", "Unable to connect to the running instance.")
            return
        # Prepare the message with potential arguments
        message = {
            'action': 'open_new_tab',
            'folder': self.args.folder if self.args.folder else None,
            'command': self.args.command if self.args.command else None
        }
        message_json = json.dumps(message).encode('utf-8')
        # Send the message length first
        length = len(message_json)
        socket.write(bytes(f"{length:08}", 'utf-8'))  # 8-byte header for message length
        socket.write(message_json)
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        logging.debug("Message sent to the primary instance.")

    @Slot()
    def receive_message(self):
        """Handle incoming messages from new instances."""
        while self.server.hasPendingConnections():
            client_connection = self.server.nextPendingConnection()
            client_connection.readyRead.connect(lambda: self.read_socket(client_connection))

    def read_socket(self, socket):
        """Read data from the socket and perform actions."""
        # First, read the 8-byte length header
        if socket.bytesAvailable() < 8:
            return  # Not enough data yet

        length_data = socket.read(8)
        try:
            # Convert QByteArray to bytes before decoding
            length = int(bytes(length_data).decode('utf-8'))
        except ValueError:
            QMessageBox.warning(None, "Qermital", "Received invalid message length.")
            socket.disconnectFromServer()
            return

        # Wait until the full message is received
        if socket.bytesAvailable() < length:
            # Not all data received yet
            return

        message_data = socket.read(length)
        if message_data:
            # Convert QByteArray to bytes before decoding
            message = bytes(message_data).decode('utf-8')
            if self.main_window:
                self.main_window.handle_new_instance_message(message)
            logging.debug("Received message from a new instance.")
        socket.disconnectFromServer()


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Qermital Terminal Emulator")
    parser.add_argument('--new', '-n', action='store_true', help='Create a new instance of Qermital')
    parser.add_argument('--folder', '-f', type=str, default=None, help='Initial directory for the terminal')
    parser.add_argument('--command', '-c', type=str, default=None, help='Command to execute on startup')
    parser.add_argument('--tray', '-t', action='store_true', help='Start the application minimized to the system tray')
    parser.add_argument('--double', '-d', action='store_true', help='Start the application with a dual pane layout. \nThis works on initial launch or when combined with --new')
    parser.add_argument('--max', '-m', action='store_true', help='Start the application maximized')
    return parser.parse_args()

def main():
    """Main function to run the application."""
    args = parse_arguments()

    if args.new:
        # Launch a new instance regardless of existing instances
        app = QApplication(sys.argv)
        qdarktheme.setup_theme()

        '''
        # Apply custom stylesheet if it exists - optional
        qss_path = Path(__file__).parent / "chros_style.qss"
        if qss_path.exists():
            try:
                with open(qss_path, "r") as f:
                    app.setStyleSheet(f.read())
                logging.debug("Custom stylesheet loaded successfully.")
            except Exception as e:
                QMessageBox.warning(None, "Style Error", f"Error loading style: {e}")
                logging.error(f"Error loading stylesheet: {e}")
        '''

        terminal_emulator = TerminalEmulator(
            initial_directory=args.folder,
            command=args.command,
            start_minimized=args.tray,
            start_double_pane=args.double,
            start_maximized=args.max
        )

        if not args.tray:
            terminal_emulator.show()
            logging.debug("Terminal emulator window shown.")

        sys.exit(app.exec())
    else:
        # Enforce single-instance behavior
        app = SingleInstanceApplication(sys.argv, args)
        qdarktheme.setup_theme()

        # Apply custom stylesheet if exists
        qss_path = Path(__file__).parent / "chros_style.qss"
        if qss_path.exists():
            try:
                with open(qss_path, "r") as f:
                    app.setStyleSheet(f.read())
                logging.debug("Custom stylesheet loaded successfully.")
            except Exception as e:
                QMessageBox.warning(None, "Style Error", f"Error loading style: {e}")
                logging.error(f"Error loading stylesheet: {e}")

        terminal_emulator = TerminalEmulator(
            initial_directory=args.folder,
            command=args.command,
            start_minimized=args.tray,
            start_double_pane=args.double,
            start_maximized=args.max
        )
        app.main_window = terminal_emulator  # Assign the main window for communication
        logging.debug("Main window assigned to SingleInstanceApplication.")

        if not args.tray:
            terminal_emulator.show()
            logging.debug("Terminal emulator window shown.")

        sys.exit(app.exec())


if __name__ == '__main__':
    create_qermital_desktop_entry()
    main()
