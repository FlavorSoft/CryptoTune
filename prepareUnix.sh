#!/bin/bash
sudo nvidia-xconfig --cool-bits=31 --allow-empty-initial-configuration
sudo xinit &
export DISPLAY=:0.0
sudo nvidia-smi -pm 1
sudo nvidia-settings -c :0