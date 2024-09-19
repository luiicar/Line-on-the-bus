# Line-on-the-edge
Progetto in collaborazione con Unico Campania
#

Per l'uso del codice è necessario scaricare in locale il codice in XML a questo link: https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1481.

Estrarre il file e aggiungerlo alla cartella /Tap-Go/TapGoBus/database.

Nota: cambia il path e il nome del file netex se necessario!

per Debian:
user: Debian
pw: debian

- il file tap_go_bus.sh si avvia in automatico all'avvio del pc (vedi caso 2a per intervenire sul processo)
- per avviare il file infomobility.sh: sh infomobility.sh


---- Comandi utili aggiuntivi ----
Caso 1: git pull manuale.

git fetch
git reset --hard HEAD
git merge '@{u}'

--------

Caso 2a: Il file tap_go_bus.service è modificato o bisogna intervenire sul processo.

sudo cp /home/debian/Tap-Go/TapGoBus/vm/tap_go_bus.service /etc/systemd/system/tap_go_bus.service
sudo chmod +x /home/debian/Tap-Go/tap_go_bus.service
sudo systemctl daemon-reload
sudo systemctl enable tap_go_bus
sudo systemctl start tap_go_bus
sudo systemctl stop tap_go_bus (per stoppare il processo)
sudo systemctl restart tap_go_bus (per riavviare il processo)
sudo systemctl status tap_go_bus (per monitorare lo stato del processo)


Caso 2b: Il file tap_go_bus.sh è modificato.

sudo cp /home/debian/Tap-Go/TapGoBus/vm/tap_go_bus.sh /home/debian/Tap-Go/tap_go_bus.sh
sudo chmod +x /home/debian/Tap-Go/tap_go_bus.py


Caso 2c: Il file infomobility.sh è modificato.
sudo cp /home/debian/Tap-Go/TapGoBus/vm/infomobility.sh /home/debian/Tap-Go/infomobility.sh
sudo chmod +x /home/debian/Tap-Go/infomobility.py

--------

Caso 3: Bisogna riclonare manualmente il git in VM.

git clone --no-checkout https://github.com/luiicar/Tap-Go.git
cd Tap-Go
git config core.sparseCheckout true
nano .git/info/sparse-checkout (e scrivere al suo interno incolonnati i file e cartelle da clonare)
git checkout
