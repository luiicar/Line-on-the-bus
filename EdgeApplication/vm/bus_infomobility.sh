#!/bin/bash


PROJECT_DIR="/home/debian/Line-on-the-edge"

# Attiva l'ambiente virtuale
source "$PROJECT_DIR/EdgeApplication/venv/bin/activate"

# Avvia il programma
cd EdgeApplication
"$PROJECT_DIR/EdgeApplication/venv/bin/python" "$PROJECT_DIR/EdgeApplication/bus_infomobility.py"
