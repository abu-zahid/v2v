# confirm that the user is sure to proceed
read -p "This will delete the existing repo and clone a new one. Are you sure you want to proceed? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "Exiting..."
    exit 1
fi


# Delete old repo
cd /home/ubuntu/
rm -rf lifewink_ai_voice_chat

# clone the repo
git clone -b dev git@github.com:hossain-techjays/lifewink_ai_voice_chat.git
cd lifewink_ai_voice_chat
cp .env.example .env

# create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip3 install -r requirements.txt

# configure systemd to run the app
sudo systemctl stop lifewink_ai_voice_chat
sudo cp /home/ubuntu/deployment_scripts/lifewink_ai_voice_chat.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable lifewink_ai_voice_chat
sudo systemctl restart lifewink_ai_voice_chat


# configure nginx to point to the app
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /home/ubuntu/deployment_scripts/lifewink_ai_voice_chat.conf /etc/nginx/conf.d/
sudo usermod -aG ubuntu www-data

sudo systemctl restart nginx

echo "[$(date)] App installed." >> /var/log/lifewink_ai_voice_chat/setup.log
