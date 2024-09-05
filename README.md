# Tap-Go
Progetto per Unico Campania
#

Per l'uso del codice è necessario scaricare in locale il codice in XML a questo link: https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1481.

Estrarre il file e aggiungerlo alla cartella /Tap-Go/TapGoBus/database.

Nota: cambia il path e il nome del file netex se necessario!

per Debian:
user: Debian
pw: debian



---- Comandi utili aggiuntivi ----
Caso 1: git pull dà errore e bisogna sovrascrivere il branch locale /Tap-Go.

git fetch
git reset --hard HEAD
git merge '@{u}'

--------

Caso 2: Il file systemd service è modificato o bisogna intervenire sul processo.

sudo cp /home/debian/Tap-Go/TapGoBus/vm/tap_go_bus.service /etc/systemd/system/tap_go_bus.service
sudo systemctl daemon-reload
sudo systemctl enable tap_go_bus
sudo systemctl start tap_go_bus
sudo systemctl stop tap_go_bus (per stoppare il processo)
sudo systemctl restart tap_go_bus (per riavviare il processo)
sudo systemctl status tap_go_bus (per monitorare lo stato del processo)

--------

Caso 3: Bisogna riclonare il git in VM.

sudo apt install python 3
sudo apt install pip
cd /home/debian/Tap-Go/TapGoBus/
rm -r venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
chmod +x tap_go_bus.py
chmod +x infomobility.py
source venv/bin/deactivate
chmod 777 /etc/systemd/system/tap_go_bus.service
cd /home/debian

git clone --no-checkout https://github.com/luiicar/Tap-Go.git
cd Tap-Go
git config core.sparseCheckout true
nano .git/info/sparse-checkout (e scrivere al suo interno incolonnati i file e cartelle da clonare)
git checkout



N.B.: è buona norma, in ogni caso, riavviare la VM.

sudo reboot now