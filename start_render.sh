#!/usr/bin/env bash

# Auto-detect and link to persistent volume if mounted at Render path
if [ -d "/opt/render/project/src/data" ] && [ ! -L "data" ]; then
  echo "Found persistent volume mounted at /opt/render/project/src/data. Linking /app/data -> /opt/render/project/src/data..."
  # If the volume is empty, copy repository defaults
  if [ ! -f "/opt/render/project/src/data/market_caps.json" ]; then
    echo "Initializing volume with repository defaults..."
    cp -r data/* /opt/render/project/src/data/ 2>/dev/null || true
  fi
  rm -rf data
  ln -s /opt/render/project/src/data data
  echo "Persistent symlink created successfully!"
fi

# Create directories on the persistent disk volume if they don't exist
mkdir -p data/reports
mkdir -p data/cache
mkdir -p data/mto

# Populate persistent disk with default data files if empty
if [ ! -f "data/market_caps.json" ]; then
  echo "Initializing persistent volume with default data files from repository..."
  cp -r data_defaults/* data/ 2>/dev/null || true
  echo "Default data files initialized!"
fi

# Migrate reports to persistent volume if reports is not yet a symlink
if [ ! -L "reports" ]; then
  if [ -d "reports" ]; then
    echo "Migrating existing reports to persistent volume..."
    cp -r reports/* data/reports/ 2>/dev/null || true
    rm -rf reports
  fi
  ln -s data/reports reports
  echo "Created symlink for reports -> data/reports"
fi

# Start the web server
echo "Starting Minervini OS Dashboard..."
python server.py
