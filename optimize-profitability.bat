pushd %~dp0
pip install -r requirements.txt
python run.py --mode 2 --loadPreset --dollarPerMHash 0.0966 --powerCost 0.36 --miner t-rex