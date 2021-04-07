# EtherTune
Python script to automatically find optimized and stable GPU overclock settings to mine Ethereum

## Warning
As this software needs to be run as admin, do not use it if you are not sure what you are doing! The software will not try to steal your data in any way, but **i'm only some dude from the internet** so please do not trust me on that :)

# What it does
This software does exactly what you would do manually to reach peak speeds/efficiency on your GPUs - but in parallel and without the effort.

### Finding maximum Memory OC
The software will start overclocking your memory until either the mining software crashes or your GPU created invalid shares. This will help in reaching the maximum possible speed.

### Finding minimum Core Clock
After finding the maximum possible memory clock, the software will start reducing the core clock until a significant decrease in speed is detected. This will help decreasing the power consumption and temperatures of your GPUs.

### Finding minimum Power Limits
After clocks are fine tuned, each GPUs power limit will be reduced to lower temperatures and increase efficiency (lower power costs). There are two modes to choose from:
Mode 1: Maximum Efficiency (default): your GPU will probably not reach it's top hash rate, but it will be the most efficient (power/hash) you can achieve
Mode 2: Maximum Speed (hybrid): Your GPU will run some kHashes below it's maximum speed but can achieve this with a lot less power than default (see "margin"-parameter)

### Tuning all GPUs in parallel
This software tracks your GPUs state every second, creates statistics from that and automatically sets your GPUs to your preferred model. All GPUs are tuned at the same time, therefore it is fast and accurate in it's decision making without writing down hundreds of values, speeds and efficiencies manually.

### Link to YouTube - Software in action
[![EtherTune Demo on youtube](https://img.youtube.com/vi/tJo8EarZyzM/0.jpg)](https://www.youtube.com/watch?v=tJo8EarZyzM)

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
- [Python 3.6 or higher installed](https://www.python.org/downloads/)
- executing script with Administrative Access (open CMD with admin privileges or right-click "start.bat" -> run as admin)
- installed packages from requirements.txt, can be done via **"pip install -r requirements.txt"**
- close MSI Afterburner (if running)

## Usage
The tool can be run as-is via the command: **"python run.py"**, it will pick default values for tuning which might not be perfect - but will work. In order to change clocks, **it is required to run the executing command line or batch-script with admin privileges (see warning above!).**
```
run.py --mode <0 (efficiency) / 1 (speed)> --devices <0,1..nbr of GPUs> --fans <speed for each GPU> --steps <stepsize for OC> --shares <nbr of shares for validation> --datapoints <nbr of Datapoints for validation> --offset <for comparing speeds> --coreUC <core underclock values> --memOC <memory overclock values> --powerLimit <power limits>
```
See file **"start.bat"** for a list of available parameters or see below list:
* --mode<-t>: Defines which optimization mode for power limit should be applied, "--mode 0" (Efficiency) "--mode 1 (Speed)
* --devices<-d>: list of GPUs by id that should be tuned, seperated by commas e.g. "--devices 0,1,2,3"
* --fans<-f>: speed of fans in percentage per GPU, separated by commas e.g. "--fans 70,66,50,80"
* --steps<-s>: stepsize to in/decrease memory and core clocks per run e.g. "--steps 5" will increase or decrease clocks 5 Mhz at a time - lower values increase accuracy of result but take longer time to complete the overall process
* --shares<-x>: number of shares each GPU needs to generate before settings are validated e.g. "--shares 5". More shares increases stability but increases overall process time
* --datapoints<-y>: minimum number of datapoints which are required to compare results e.g. "--datapoints 20". Higher values mean more reliable results. Duration impact is minimal.
* --offset<-o>: to compare speed results e.g. "--offset 0.35". If set too low, your efficiency will suffer. If set too high, the efficiency will be fine but your speed result will suffer, feel free to play with this but 0.35 is a good starting point.
* --coreUC<-c>: starting value of core underclock e.g. "--coreUC -200" will begin the core underclock with -200mhz. Separate values for multiple GPUs with comma e.g. "--coreUC -200,-100,-50"
* --memOC<-m>: starting value of memory overclock e.g. "--memOC 1000" will begin the memory overclock with +1000mhz. Separate values for multiple GPUs with comma e.g. "--memOC 1000, 800, 550"
* --powerLimit<-p>: starting value of power limit e.g. "--powerLimit 240" will begin power limit reduction at 240 watts. Separate values for multiple GPUs with comma e.g. "--powerLimit 240,230,250"
* --powercost<-e>: define how much your power costs $/kWh, needed to calculate profitability in mode 2
* --dollarPerMHash<-i>: define the value of 1 MHash, needed to calculate profitability in mode 2 - you can find out via https://whattomine.com/ - or pick 0.0966 (2020-04-07)