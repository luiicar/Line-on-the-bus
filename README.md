# Tap-Go
Progetto per Unico Campania
#

Per l'uso del codice è necessario scaricare in locale il codice in XML a questo link: https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1481.

Estrarre il file e aggiungerlo alla cartella /Tap-Go/TapGoBus.

Nota: cambia il path e il nome del file netex se necessario!



---- Comandi utili aggiuntivi ----
Caso 1: git pull dà errore e bisogna sovrascrivere il branch locale /Tap-Go.

git fetch
git reset --hard HEAD
git merge '@{u}'

Caso 2: Il file systemd service è modificato o bisogna intervenire sul processo.

cp /home/debian/Tap-Go/tap_go_bus.service /etc/systemd/system/tap_go_bus.service
sudo systemctl daemon-reload
sudo systemctl enable tap_go_bus
sudo systemctl start tap_go_bus
sudo systemctl stop tap_go_bus (per stoppare il processo)
sudo systemctl restart tap_go_bus (per riavviare il processo)
sudo systemctl status tap_go_bus (per monitorare lo stato del processo)


N.B.: è buona norma, in ogni caso, riavviare la VM.

sudo reboot now