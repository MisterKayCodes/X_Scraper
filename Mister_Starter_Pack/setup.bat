@echo off
echo Setting up virtual environment...
python -m venv venv
echo Activating virtual environment and installing requirements...
call venv\Scripts\activate
pip install -r requirements.txt
echo Setup complete!
pause
