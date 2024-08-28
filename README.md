# Tap-Go
Progetto per Unico Campania
#

Per l'uso del codice è necessario scaricare in locale il codice in XML a questo link: https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1481.

Estrarre il file se necessario e aggiungerlo alla cartella Tap-Go/TapGoBus.

Nota: cambia il path e il nome del file netex se necessario!



---- Comandi utili aggiuntivi ----
Caso 1: git pull da errore e bisognerebbe sovrascrivere il branch locale.

git fetch
git reset --hard HEAD
git merge '@{u}'

Caso 2: Il file systemd service è modificato o bisogna intervenire sul processo.

sudo systemctl daemon-reload
sudo systemctl enable tap_go_bus
sudo systemctl start tap_go_bus
sudo systemctl stop tap_go_bus

Sia in caso 1 che in caso 2 riavviare la VM.

sudo reboot now