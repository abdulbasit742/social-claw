@echo off
cd /d C:\Users\absh5\MoneyPrinterTurbo
set HTTP_PROXY=http://172.30.10.10:3128
set HTTPS_PROXY=http://172.30.10.10:3128
set http_proxy=http://172.30.10.10:3128
set https_proxy=http://172.30.10.10:3128
set NO_PROXY=localhost,127.0.0.1
set no_proxy=localhost,127.0.0.1
.\venv\Scripts\python.exe scripts\auto_factory.py >> logs\auto_factory_run.log 2>&1
