#!/bin/bash

# Attiva l'ambiente virtuale
source /home/debian/Tap-Go/TapGoBus/venv/bin/activate

# Esegui git pull
cd /home/debian/Tap-Go/
git fetch
git reset --hard HEAD
git merge '@{u}'

# Controlla se requirements.txt è cambiato e nel caso scarica i pacchetti
cd TapGoBus
if git diff --name-only HEAD@{1} HEAD | grep -q "requirements.txt"; then
    pip install -r requirements.txt
fi

# Avvia il programma
python /home/debian/Tap-Go/TapGoBus/tap_go_bus.py
