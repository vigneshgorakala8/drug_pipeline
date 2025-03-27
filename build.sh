#!/usr/bin/env bash

# Install Chrome using a more reliable method for Render
apt-get update
apt-get install -y wget gnupg2 apt-utils
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

# Verify Chrome installation
echo "Verifying Chrome installation..."
which google-chrome || echo "Chrome not found in PATH"
google-chrome --version || echo "Failed to get Chrome version"

# Install ChromeDriver
echo "Installing ChromeDriver..."
CHROME_VERSION=$(google-chrome --version 2>/dev/null | awk '{print $3}' | cut -d '.' -f 1)
if [ -z "$CHROME_VERSION" ]; then
  echo "Failed to get Chrome version, using default version 114"
  CHROME_VERSION=114
fi
echo "Chrome version: $CHROME_VERSION"

CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
if [ -z "$CHROMEDRIVER_VERSION" ]; then
  echo "Failed to get ChromeDriver version, using default version 114.0.5735.90"
  CHROMEDRIVER_VERSION="114.0.5735.90"
fi
echo "ChromeDriver version: $CHROMEDRIVER_VERSION"

wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

# Verify ChromeDriver installation
echo "Verifying ChromeDriver installation..."
which chromedriver || echo "ChromeDriver not found in PATH"
chromedriver --version || echo "Failed to get ChromeDriver version"

# Set environment variables for the app to use
echo "export CHROME_BIN=$(which google-chrome)" >> ~/.bashrc
echo "export CHROMEDRIVER_PATH=$(which chromedriver)" >> ~/.bashrc

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt 