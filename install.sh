#!/bin/bash
# install.sh
# Installation script for TempMonitor.

# Stop on any error
set -e

echo "=========================================="
echo "    TempMonitor Installer"
echo "=========================================="

# --- 1. Define Variables ---
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_EXEC="python3"
VENV_DIR="$PROJECT_DIR/venv"
VENV_PYTHON_EXEC="$VENV_DIR/bin/python"

# File Paths
KB_TEMPLATE="$PROJECT_DIR/tempmonitor.desktop"
KB_INSTALL_LOC="$HOME/.local/share/applications/tempmonitor.desktop"

DATA_DIR="$HOME/tempmonitor/data"
TEMP_DESKTOP_FILE="/tmp/tempmonitor_temp.desktop"

echo "Project path: $PROJECT_DIR"

# --- 2. Install System Dependencies ---
echo ""
echo "--- [Step 1/5] Checking System Dependencies ---"
sudo apt-get update
sudo apt-get install -y \
    python3-tk python3-dev swig python3-venv liblgpio-dev numlockx \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev \
    zlib1g-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    libgstreamer1.0-0 gstreamer1.0-plugins-base \
    libmtdev-dev xclip xsel libjpeg-dev

# --- 3. Install Python Dependencies ---
echo ""
echo "--- [Step 2/5] Setting up Python Environment ---"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_EXEC -m venv "$VENV_DIR"
fi

echo "Installing/Updating Python requirements..."
"$VENV_PYTHON_EXEC" -m pip install --upgrade pip setuptools wheel
"$VENV_PYTHON_EXEC" -m pip install -r requirements.txt
# "$VENV_PYTHON_EXEC" -m pip install kivy[full]
# "$VENV_PYTHON_EXEC" -m pip install kivy_garden.graph
# "$VENV_PYTHON_EXEC" -m pip install w1thermsensor
# "$VENV_PYTHON_EXEC" -m pip install matplotlib

# --- 4. Create Desktop Shortcut ---
echo ""
echo "--- [Step 3/5] Installing Desktop Shortcut ---"

# Ensure local applications directory exists
mkdir -p "$HOME/.local/share/applications"

# --- INSTALL TEMPMONITOR SHORTCUT ---
# We use the template logic: Check for template, else generate default.
if [ -f "$KB_TEMPLATE" ]; then
    echo "Using existing TempMonitor template..."
    cp "$KB_TEMPLATE" "$TEMP_DESKTOP_FILE"
    
    EXEC_CMD="$VENV_PYTHON_EXEC $PROJECT_DIR/src/main.py"
    ICON_PATH="$PROJECT_DIR/src/assets/thermometer.png"
    
    # Replace placeholders using | as delimiter to avoid path clashes
    sed -i "s|Exec=PLACEHOLDER_EXEC_PATH|Exec=$EXEC_CMD|g" "$TEMP_DESKTOP_FILE"
    sed -i "s|Path=PLACEHOLDER_PATH|Path=$PROJECT_DIR|g" "$TEMP_DESKTOP_FILE"
    sed -i "s|Icon=PLACEHOLDER_ICON_PATH|Icon=$ICON_PATH|g" "$TEMP_DESKTOP_FILE"
    
    mv "$TEMP_DESKTOP_FILE" "$KB_INSTALL_LOC"
else
    echo "Creating default TempMonitor shortcut..."
    cat <<EOF > "$KB_INSTALL_LOC"
[Desktop Entry]
Version=1.0
Type=Application
Name=TempMonitor
Comment=Temperature Monitor
Path=$PROJECT_DIR
Exec=$VENV_PYTHON_EXEC $PROJECT_DIR/src/main.py
Icon=$PROJECT_DIR/src/assets/thermometer.png
Terminal=false
StartupNotify=true
Categories=Application;Other;
StartupWMClass=TempMonitor
EOF
fi

# Make executable
chmod +x "$KB_INSTALL_LOC"
echo " - TempMonitor shortcut installed."

# --- 5. Create Data Directory ---
echo ""
echo "--- [Step 4/5] Setting up Data Directory ---"
if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    echo "Created data directory at: $DATA_DIR"
else
    echo "Data directory already exists."
fi

# --- 6. Set Permissions ---
echo ""
echo "--- [Step 5/5] Finalizing Permissions ---"
chmod -R 755 "$PROJECT_DIR"

echo ""
echo "=========================================="
echo "    Installation Complete!"
echo "    You can now launch TempMonitor from the application menu."
echo "=========================================="
