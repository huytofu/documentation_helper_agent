#!/bin/bash
# Build script for Vercel deployment

# Print current directory and files for debugging
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Check for .env file
if [ -f .env ]; then
  echo "Found .env file in root directory"
else
  echo "No .env file found, creating from .env.example"
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
  else
    echo "Warning: No .env.example file found"
  fi
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Navigate to UI directory and install npm dependencies
echo "Installing frontend dependencies..."
cd ui

# Create symbolic link to root .env file to ensure frontend uses the same env variables
if [ ! -f .env ] && [ -f ../.env ]; then
  echo "Creating symbolic link to root .env file for frontend"
  ln -s ../.env .env
fi

npm install

# Build the frontend
echo "Building frontend..."
npm run build

# Return to root directory
cd ..
echo "Build completed successfully!" 