# EtherTune
Python script to automatically find optimized and stable GPU overclock settings to mine Ethereum

## Warning
As this software needs to be run as admin, do not use it if you are not sure what you are doing! The software will not try to steal your data in any way, but **i'm only some dude from the internet** so please do not trust me on that :)

### Mining Software
There is a miner (GMiner 2.49) included, but as code cannot be easily checked i strongly recommend you download and **add your own mining binaries** and rename (if needed) to "miner.exe".

## Limitations
Currenty, the tool comes with some limitation
- OS: Windows 10 (Ubuntu is planned)
- Mining Software: GMiner (NBMiner and others planned)

## Requirements
Following requirements need to be met in order for the tool to work properly
- NVIDIA Driver installed (especially nvidia-smi)
- Up-to-date Windows 10
- executing script with Administrative Access
- installed software from requirements.txt

## Usage
The tool can be run as-is via the command: **"python run.py"**, it will pick default values for tuning which might not be perfect - but will work. In order to change clocks, **it is required to run the executing command line or batch-script with admin privileges (see warning above!).**
```
run.py --mode <0 (efficiency) / 1 (speed)> --devices <0,1..nbr of GPUs> --fans <speed for each GPU> --steps <stepsize for OC> --shares <nbr of shares for validation> --datapoints <nbr of Datapoints for validation> --offset <for comparing speeds> --coreUC <core underclock values> --memOC <memory overclock values> --powerLimit <power limits>
```
See file **"start.bat"** for a list of available parameters or see below list:
* --mode: Defines which optimization mode for power limit should be applied, "--mode 0" (Efficiency) "--mode 1 (Speed)
* --devices: list of GPUs by id that should be tuned, seperated by commas e.g. "--devices 0,1,2,3"
* --fans: speed of fans in percentage per GPU, separated by commas e.g. "--fans 70,66,50,80"
* --steps: stepsize to in/decrease memory and core clocks per run e.g. "--steps 5" will increase or decrease clocks 5 Mhz at a time - lower values increase accuracy of result but take longer time to complete the overall process
* --shares: number of shares each GPU needs to generate before settings are validated e.g. "--shares 5". More shares increases stability but increases overall process time
* --datapoints: minimum number of datapoints which are required to compare results e.g. "--datapoints 20". Higher values mean more reliable results. Duration impact is minimal.
* --offset: to compare speed results e.g. "--offset 0.35". If set too low, your efficiency will suffer. If set too high, the efficiency will be fine but your speed result will suffer, feel free to play with this but 0.35 is a good starting point.
* --coreUC: starting value of core underclock e.g. "--coreUC -200" will begin the core underclock with -200mhz. Separate values for multiple GPUs with comma e.g. "--coreUC -200,-100,-50"
* --memOC: starting value of memory overclock e.g. "--memOC 1000" will begin the memory overclock with +1000mhz. Separate values for multiple GPUs with comma e.g. "--memOC 1000, 800, 550"
* --powerLimit: starting value of power limit e.g. "--powerLimit 240" will begin power limit reduction at 240 watts. Separate values for multiple GPUs with comma e.g. "--powerLimit 240,230,250"
