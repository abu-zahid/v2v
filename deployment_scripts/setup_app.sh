#!/bin/bash

# Confirm that the user is sure to proceed
read -p "This will install/update the AI Voice Chat application. Are you sure you want to proceed? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "Exiting..."
    exit 1
fi

# Set up application directory
APP_DIR="/home/$(whoami)/ai_voice_chat/"

# Check if directory exists, if so, ask to delete
if [ -d "$APP_DIR" ]; then
    read -p "The directory $APP_DIR already exists. Do you want to remove it and start fresh? (y/n): " remove_dir
    if [ "$remove_dir" = "y" ]; then
        rm -rf "$APP_DIR"
    else
        echo "Will try to update the existing installation."
    fi
fi

# Create directory if it doesn't exist
if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
fi

# Move to the app directory
cd "$APP_DIR"

# Copy all the necessary files here
# For simplicity, we'll copy from the current directory
# In a real-world scenario, you might clone from a repository
echo "Copying application files..."


# clone the repo
git clone -b main git@github.com:abu-zahid/v2v.git
cd v2v
cp .env.example .env
APP_DIR="/home/$(whoami)/ai_voice_chat/v2v/"

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt
git clone https://github.com/nari-labs/dia.git
pip3 install -q ./dia
pip3 install -q soundfile

# Configure systemd to run the app
echo "Configuring systemd service..."
sudo systemctl stop ai_voice_chat 2>/dev/null || true

# Create systemd service file
cat > ai_voice_chat.service << EOF
[Unit]
Description=Uvicorn instance to serve the AI Voice Chat
After=network.target

[Service]
User=$(whoami)
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
ExecStart=$APP_DIR/.venv/bin/uvicorn main:app --uds .sock --workers 4

[Install]
WantedBy=multi-user.target
EOF

sudo cp ai_voice_chat.service /etc/systemd/system/

# Create nginx config
echo "Configuring nginx..."
cat > ai_voice_chat.conf << EOF
server {
    listen 80;
    server_name _;

    location /demo {
        alias $APP_DIR/demo_frontend;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_redirect off;
        proxy_buffering off;
        proxy_pass http://ai_voice_chat;
    }
}

upstream ai_voice_chat {
    server unix:$APP_DIR/.sock;
}

map \$http_upgrade \$connection_upgrade {
        default upgrade;
        '' close;
}
EOF

sudo cp ai_voice_chat.conf /etc/nginx/conf.d/

# Enable nginx configuration
sudo rm -f /etc/nginx/sites-enabled/default
sudo usermod -aG $(whoami) www-data

# Restart services
echo "Restarting services..."
sudo systemctl daemon-reload
sudo systemctl enable ai_voice_chat
sudo systemctl restart ai_voice_chat
sudo systemctl restart nginx

echo "[$(date)] App installed." >> /var/log/ai_voice_chat/setup.log
echo "Installation complete! The application is now running."