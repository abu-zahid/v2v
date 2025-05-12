#!/bin/bash

# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Python dependencies
sudo apt-get install -y python3-venv python3-pip

# Install nginx for web server
sudo apt-get install nginx -y

# Enable and start nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Setup logs directory
sudo mkdir -p /var/log/ai_voice_chat

# Create and set permissions for log files
sudo touch /var/log/ai_voice_chat/ai_voice_chat.log
sudo chmod 777 /var/log/ai_voice_chat/ai_voice_chat.log

sudo touch /var/log/ai_voice_chat/setup.log
sudo chmod 777 /var/log/ai_voice_chat/setup.log

echo "[$(date)] Dependencies installed." >> /var/log/ai_voice_chat/setup.log

# Check if firewall is enabled, if yes, allow HTTP and HTTPS
if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 'Nginx Full'
    echo "[$(date)] Firewall rules updated for Nginx." >> /var/log/ai_voice_chat/setup.log
fi

# For GCP, we need to make sure that the VM has the right permissions
# Note: Unlike AWS IAM roles, GCP uses service accounts
# This script doesn't handle that, as it should be configured when creating the VM
echo "[$(date)] GCP: Ensure your VM has the appropriate service account attached." >> /var/log/ai_voice_chat/setup.log