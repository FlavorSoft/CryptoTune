#!/bin/bash
nvidia-xconfig -a --allow-empty-initial-configuration --cool-bits=28 -o nvidia-xorg.conf
sudo tmux new -d 'sudo X -config nvidia-xorg.conf :1'
export DISPLAY=:1
nvidia-settings -a [gpu:0]/GPUFanControlState=1