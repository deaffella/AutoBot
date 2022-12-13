#!/bin/bash

#if [[ "$EUID" -ne 0 ]]; then
#  echo "Please run as root"
#  exit
#fi

clear

#printf "running:
#docker exec -it donkey_car ./Autobot_Platform.py
#
#"
#docker exec -it donkey_car bash
#docker exec -it donkey_car ./Autobot_Platform.py


TMUX_SESS_NAME=donkeycar
DOCKER_COMMAND='docker exec -it donkey_car ./Autobot_Platform.py'

#tmux attach -t ${TMUX_SESS_NAME};              # open (attach) tmux session.
docker restart donkey_car
tmux kill-server

tmux ls

tmux new-session -d -s ${TMUX_SESS_NAME} ${DOCKER_COMMAND};    # start new detached tmux session, run htop
tmux split-window -h;                          # split the detached tmux session
tmux send 'jtop' ENTER;                        # send 2nd command 'htop -t' to 2nd pane. I believe there's a `--target` option to target specific pane.
tmux split-window -v;                          # split the detached tmux session
tmux attach -t ${TMUX_SESS_NAME};              # open (attach) tmux session.