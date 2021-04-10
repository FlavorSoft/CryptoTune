pushd %~dp0
pip install -r requirements.txt
python run.py --mode 2 --fans 71 --steps 5 --shares 3 --datapoints 20 --offset 0.3 --coreUC -50 --memOC 200 --powerLimit 240 --powerCost 0.36 --dollarPerMHash 0.096 --loadPreset