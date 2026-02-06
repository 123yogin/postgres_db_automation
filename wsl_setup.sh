#!/bin/bash
# WSL Ubuntu Setup Script for Database Screenshot Automation

echo "Setting up WSL Ubuntu environment..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install desktop environment (lightweight XFCE)
sudo apt install xfce4 xfce4-goodies -y

# Install Xvfb and screenshot tools
sudo apt install xvfb imagemagick scrot -y

# Install Python and PostgreSQL client
sudo apt install python3 python3-pip python3-full python3-venv postgresql-client -y

# Install Python development headers and PostgreSQL libraries
sudo apt install python3-dev libpq-dev build-essential -y

# Install psycopg2 via apt (more reliable)
sudo apt install python3-psycopg2 -y

# Install window management tools
sudo apt install wmctrl xdotool -y

# Create virtual environment for Python packages
echo "Creating virtual environment..."
python3 -m venv ~/db_automation_venv

# Activate virtual environment and install packages
echo "Installing Python packages in virtual environment..."
source ~/db_automation_venv/bin/activate
pip install psycopg2-binary pillow pynput

echo "Setup complete! Now you can run the modified Python script."
echo "To activate virtual environment: source ~/db_automation_venv/bin/activate"
echo "Testing installations..."
~/db_automation_venv/bin/python -c "import psycopg2; print('✓ psycopg2 installed successfully!')" || echo "✗ psycopg2 installation failed"
~/db_automation_venv/bin/python -c "from PIL import Image; print('✓ PIL installed successfully!')" || echo "✗ PIL installation failed"
~/db_automation_venv/bin/python -c "import pynput; print('✓ pynput installed successfully!')" || echo "✗ pynput installation failed"