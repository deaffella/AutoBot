#!/bin/bash

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root"
  exit
fi
clear


# Запоминаем папку запуска
export project_dir_path=`pwd`/

# Запоминаем платформу системы
export OS_PLATFORM=`uname -s`/`uname -m`

export DISPLAY=:0
xhost +


echo ""
echo ""
echo "=============================================="
echo 'RUNNING "build_project.sh"'
echo ""
echo "DISPLAY: "
echo ${DISPLAY}
echo ""
echo "HOSTNAME: "
echo ${HOSTNAME}
echo ""
echo ""
echo "project_dir_path: "
echo ${project_dir_path}
echo ""
echo "OS_PLATFORM: "
echo ${OS_PLATFORM}
echo "=============================================="
echo ""


sleep 1

printf "

export DISPLAY=${DISPLAY}
xhost +
" >> ~/.bashrc


# Disabling the Wi-Fi Power Management on an Nvidia Jetson
# based on https://github.com/robwaat/Tutorial/blob/master/Jetson%20Disable%20Wifi%20Power%20Management.md
printf "[connection]
#wifi.powersave = 3
wifi.powersave = 2
" > /etc/NetworkManager/conf.d/default-wifi-powersave-on.conf


sudo apt update
#sudo apt upgrade -y
sudo apt install -y curl \
                    wget \
                    git \
                    nano \
                    dos2unix \
                    python3 \
                    python3-pip\
                    htop \
                    tmux \
                    net-tools \
                    network-manager \
                    v4l-utils \
                    docker docker-compose \
                    joystick

sudo -H pip3 install -U jetson-stats

printf "



"

docker volume create portainer_data
docker run -d -p 9000:9000 --name=portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer


chmod 777 -R *
chmod +x -R *.sh
chmod +x -R *.py
dos2unix -R *.py