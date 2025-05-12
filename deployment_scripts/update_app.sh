cd /home/ubuntu/lifewink_ai_voice_chat
git pull

source .venv/bin/activate
pip3 install -r requirements.txt
git clone https://github.com/nari-labs/dia.git
pip3 install -q ./dia
pip3 install -q soundfile

sudo systemctl restart lifewink_ai_voice_chat

echo "[$(date)] App updated." >> /var/log/lifewink_ai_voice_chat/setup.log
