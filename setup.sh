#!/bin/bash
# Download Vosk Italian model
mkdir -p model
cd model
if [ ! -f "vosk-model-it-0.4.tar.gz" ]; then
    wget https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip
fi
tar -xzf vosk-model-it-0.4.tar.gz
mv vosk-model-it-0.4/* .
rm -rf vosk-model-it-0.4

# Install Python dependencies
cd ..
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

sudo apt-get install libgirepository1.0-dev libcairo2-dev gir1.2-gtk-3.0 python3-dev libappindicator3-dev

