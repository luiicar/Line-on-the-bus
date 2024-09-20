#!/bin/bash


PROJECT_DIR="/home/debian/Tap-Go"

# Attiva l'ambiente virtuale
source "$PROJECT_DIR/EdgeApplication/venv/bin/activate"

# Avvia il programma
cd EdgeApplication
"$PROJECT_DIR/EdgeApplication/venv/bin/python" "$PROJECT_DIR/EdgeApplication/bus_infomobility.py"
