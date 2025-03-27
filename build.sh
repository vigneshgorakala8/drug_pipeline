#!/usr/bin/env bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting Chrome and ChromeDriver installation..."

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
CHROME_PATH=$(which google-chrome)
echo "Chrome path: $CHROME_PATH"
google-chrome --version || echo "Failed to get Chrome version"

# Install ChromeDriver
echo "Installing ChromeDriver..."
CHROME_VERSION=$(google-chrome --version 2>/dev/null | awk '{print $3}' | cut -d '.' -f 1)
if [ -z "$CHROME_VERSION" ]; then
  echo "Failed to get Chrome version, using default version 114"
  CHROME_VERSION=114
fi
echo "Chrome version: $CHROME_VERSION"

# Try to get the matching ChromeDriver version
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
if [ -z "$CHROMEDRIVER_VERSION" ]; then
  echo "Failed to get ChromeDriver version for Chrome $CHROME_VERSION, trying alternative approach"
  # Try to get the latest ChromeDriver version
  CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE")
  
  if [ -z "$CHROMEDRIVER_VERSION" ]; then
    echo "Failed to get latest ChromeDriver version, using default version 114.0.5735.90"
    CHROMEDRIVER_VERSION="114.0.5735.90"
  fi
fi
echo "ChromeDriver version: $CHROMEDRIVER_VERSION"

# Download and install ChromeDriver
wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

# Verify ChromeDriver installation
echo "Verifying ChromeDriver installation..."
which chromedriver || echo "ChromeDriver not found in PATH"
CHROMEDRIVER_PATH=$(which chromedriver)
echo "ChromeDriver path: $CHROMEDRIVER_PATH"
chromedriver --version || echo "Failed to get ChromeDriver version"

# Set environment variables for the app to use
echo "export CHROME_BIN=$CHROME_PATH" >> ~/.bashrc
echo "export CHROMEDRIVER_PATH=$CHROMEDRIVER_PATH" >> ~/.bashrc
echo "export CHROME_BIN=$CHROME_PATH" >> ~/.profile
echo "export CHROMEDRIVER_PATH=$CHROMEDRIVER_PATH" >> ~/.profile

# Make environment variables available immediately
export CHROME_BIN=$CHROME_PATH
export CHROMEDRIVER_PATH=$CHROMEDRIVER_PATH

# Create a .env file for the application to read
echo "CHROME_BIN=$CHROME_PATH" > .env
echo "CHROMEDRIVER_PATH=$CHROMEDRIVER_PATH" >> .env

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install webdriver-manager as a fallback
pip install webdriver-manager

echo "Chrome and ChromeDriver installation completed." 