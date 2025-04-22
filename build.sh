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
    # Set SERVER_TYPE to vercel in the .env file
    sed -i 's/SERVER_TYPE=.*/SERVER_TYPE=vercel/g' .env
    echo "Created .env file from .env.example and set SERVER_TYPE to vercel"
  else
    echo "Warning: No .env.example file found"
    # Create minimal .env file
    echo "SERVER_TYPE=vercel" > .env
    echo "Created minimal .env file with SERVER_TYPE=vercel"
  fi
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Make sure the database directory exists for local development
if [ ! -d "data" ]; then
  echo "Creating data directory for database storage"
  mkdir -p data
fi

# Navigate to UI directory and install npm dependencies if UI exists
if [ -d "ui" ]; then
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
else
  echo "No UI directory found, skipping frontend build"
fi

echo "Build completed successfully!" 