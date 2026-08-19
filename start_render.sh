#!/usr/bin/env bash

# Auto-detect and link to persistent volume at /data if present
if [ -d "/data" ] && [ ! -L "data" ]; then
  echo "Found persistent volume mounted at /data. Linking /app/data -> /data..."
  # If /data is empty, initialize it with repository defaults
  if [ ! -f "/data/market_caps.json" ]; then
    echo "Initializing /data volume with repository defaults..."
    cp -r data/* /data/ 2>/dev/null || true
  fi
  rm -rf data
  ln -s /data data
  echo "Persistent symlink /app/data -> /data created!"
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
