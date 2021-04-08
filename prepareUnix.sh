#!/bin/bash
sudo nvidia-xconfig --cool-bits=31 --allow-empty-initial-configuration
sudo xinit &
export DISPLAY=:0.0
c
echo -ne '\n' | sudo nvidia-settings -c :0 &
nvidia-settings -a [gpu:0]/GPUFanControlState=1