REM parameterlist mode, devIds, fanSpeeds, steps, nbrOfShares, nbrOfDatapoints, marginInMH, coreUCs, memOCs, powerLimits
pip install -r requirements.txt
python run.py --mode 1 --fans 71 --steps 5 --shares 2 --datapoints 20 --offset 0.3 --coreUC -50 --memOC 200