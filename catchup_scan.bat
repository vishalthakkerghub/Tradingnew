@echo off
cd /d "%~dp0"
python catchup_scan.py >> logs\catchup_scan.log 2>&1
