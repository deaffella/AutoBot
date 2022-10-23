#!/bin/bash

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root"
  exit
fi
clear



export docker_stack_name="autobot"

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
echo "docker_stack_name: "
echo ${docker_stack_name}
echo ""
echo "project_dir_path: "
echo ${project_dir_path}
echo ""
echo "OS_PLATFORM: "
echo ${OS_PLATFORM}
echo "=============================================="
echo ""


sleep 1

cd ${project_dir_path}


### Собираем базовый образ
#docker build -t autobot:l4t_cv_tf --file dockerfiles/l4t_cv_tf.Dockerfile .


# Поднимаем контейнеры из docker-compose.yml
#docker-compose -p "${docker_stack_name}" up -d --build

docker-compose -p "${docker_stack_name}" down

#DOCKER_DEFAULT_PLATFORM=${OS_PLATFORM} \
COMPOSE_DOCKER_CLI_BUILD=1 \
DOCKER_BUILDKIT=1 \
HOSTNAME=${HOSTNAME} \
DISPLAY=${DISPLAY} \
docker-compose -p "${docker_stack_name}" up -d --build


echo ""
echo ""
echo "=============================================="
echo "BUILD SUCCESSFUL"
echo "=============================================="
echo ""
cd ${project_dir_path} && sudo chmod 777 -R *
