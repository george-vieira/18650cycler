# Cycler2 web python UI

## Install

sudo apt-get update
sudo apt-get -y install python3 python3-venv
sudo python3 -mpip upgrade

tar xvfz cycler2ui.tgz
cd cycler2ui

python3 -mvenv .
./bin/python3 -mpip install -r requirements.txt

## Run

source bin/activate

python3 main.py
