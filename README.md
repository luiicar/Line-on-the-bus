# Line-on-the-edge
Progetto in collaborazione con il Consorzio Unico Campania
#

Per l'uso del codice è necessario scaricare in locale il codice in XML a questo link: https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1481.

Estrarre il file e aggiungerlo alla cartella /Line-on-the-edge/EdgeApplication/database.


- (per Debian)    user: Debian       pw:   debian
- bus_tracker.sh si avvia in automatico all'avvio del pc (vedi caso 2a per intervenire sul processo)
- per avviare il file infomobility.sh: sh infomobility.sh


---- Comandi utili aggiuntivi ----
Caso 1: git pull manuale.

git fetch
git reset --hard HEAD
git merge '@{u}'

--------

Caso 2a: Il file bus_tracker.service è modificato o bisogna intervenire sul processo.

sudo cp /home/debian/Line-on-the-edge/EdgeApplication/vm/bus_tracker.service /etc/systemd/system/bus_tracker.service
sudo chmod +x /etc/systemd/system/bus_tracker.service
sudo systemctl daemon-reload
sudo systemctl enable bus_tracker
sudo systemctl start bus_tracker
sudo systemctl stop bus_tracker (per stoppare il processo)
sudo systemctl restart bus_tracker (per riavviare il processo)
sudo systemctl status bus_tracker (per monitorare lo stato del processo)


Caso 2b: Il file bus_tracker.sh è modificato.

sudo chmod +x /home/debian/Line-on-the-edge/EdgeApplication/bus_tracker.py


Caso 2c: Il file bus_infomobility.sh è modificato.

sudo chmod +x /home/debian/Line-on-the-edge/EdgeApplication/bus_infomobility.py

--------

Caso 3: Bisogna riclonare manualmente il git in VM.

git clone --no-checkout https://github.com/luiicar/Line-on-the-edge.git
cd Line-on-the-edge
git config core.sparseCheckout true
nano .git/info/sparse-checkout (e scrivere al suo interno incolonnati i file e cartelle da clonare)
git checkout
