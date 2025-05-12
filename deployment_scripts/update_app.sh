cd /home/ubuntu/lifewink_ai_voice_chat
git pull

source .venv/bin/activate
pip3 install -r requirements.txt

sudo systemctl restart lifewink_ai_voice_chat

echo "[$(date)] App updated." >> /var/log/lifewink_ai_voice_chat/setup.log
