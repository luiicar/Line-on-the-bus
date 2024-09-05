#!/bin/bash


PROJECT_DIR="/home/debian/Tap-Go"
update="false"


# Esegui git pull
cd "$PROJECT_DIR"
git fetch
git reset --hard HEAD
git merge '@{u}'

# Controlla se requirements.txt è cambiato
cd TapGoBus
if git diff --name-only HEAD@{1} HEAD | grep -q "requirements.txt"; then
    update="true"
    rm -r venv
    python3 -m venv venv
fi

# Attiva l'ambiente virtuale
source "$PROJECT_DIR/TapGoBus/venv/bin/activate"

# Se requirements.txt è cambiato, scarica i pacchetti
if [ "$update" == "true" ]; then
    pip install -r requirements.txt
fi

# Avvia il programma
"$PROJECT_DIR/TapGoBus/venv/bin/python" "$PROJECT_DIR/TapGoBus/tap_go_bus.py"