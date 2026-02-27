#!/bin/bash
# Download Vosk Italian model
mkdir -p model
cd model
if [ ! -f "vosk-model-it-0.4.tar.gz" ]; then
    wget https://alphacephei.com/vosk/models/vosk-model-it-0.4.tar.gz
fi
tar -xzf vosk-model-it-0.4.tar.gz
mv vosk-model-it-0.4/* .
rm -rf vosk-model-it-0.4

# Install Python dependencies
cd ..
pip install -r requirements.txt
