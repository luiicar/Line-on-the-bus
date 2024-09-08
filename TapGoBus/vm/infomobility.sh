#!/bin/bash


PROJECT_DIR="/home/debian/Tap-Go"

# Attiva l'ambiente virtuale
source "$PROJECT_DIR/TapGoBus/venv/bin/activate"

# Avvia il programma
cd "$PROJECT_DIR/TapGoBus/"
"$PROJECT_DIR/TapGoBus/venv/bin/python" "$PROJECT_DIR/TapGoBus/infomobility.py"
