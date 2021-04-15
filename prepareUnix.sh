#!/bin/bash
nvidia-xconfig -a --allow-empty-initial-configuration --cool-bits=28 -o nvidia-xorg.conf --enable-all-gpus
sleep 5
sudo tmux new -d 'sudo X -config nvidia-xorg.conf :1'
export DISPLAY=:1