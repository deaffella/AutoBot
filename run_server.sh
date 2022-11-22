#!/bin/bash

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root"
  exit
fi
clear

docker exec -it server_donkeycar ./UI_entrypoint.sh
#docker exec -it server_donkeycar bash