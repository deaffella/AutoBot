#!/bin/bash

# Скрипт для настройки udev правил для usb камеры.
# `./05_configure_usb_udev_rule.sh    (camera_device_id)
# sudo ./05_configure_usb_udev_rule.sh 1


if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root"
  exit
fi
clear

CAMERA_DEVICE_IDX=$1                            # example: 2
CAMERA_DEVICE_PATH=/dev/video${CAMERA_DEVICE_IDX}     # example: /dev/video2


ID_VENDOR_ARRAY=`udevadm info -a -n ${CAMERA_DEVICE_PATH} |grep "ATTRS{idVendor}"`
ID_PRODUCT_ARRAY=`udevadm info -a -n ${CAMERA_DEVICE_PATH} |grep "ATTRS{idProduct}"`

FIRST_ID_VENDOR=($(echo $ID_VENDOR_ARRAY | tr "    " "\n"))
FIRST_ID_PRODUCT=($(echo $ID_PRODUCT_ARRAY | tr "    " "\n"))

#SELECTED_ID_VENDOR=($(echo $FIRST_ID_VENDOR | tr 'ATTRS{idVendor}=="' "\n"))
#SELECTED_ID_PRODUCT=($(echo $FIRST_ID_PRODUCT | tr 'ATTRS{idProduct}=="' "\n"))


SELECTED_ID_VENDOR=($(echo $FIRST_ID_VENDOR | sed "s/ATTRS{idVendor}==\"//g" | sed "s/\"//g"))
SELECTED_ID_PRODUCT=($(echo $FIRST_ID_PRODUCT | sed "s/ATTRS{idProduct}==\"//g" | sed "s/\"//g"))


printf "
==============================================
RUNNING __setup/get_usb_camera_vendor_attrs.sh

CAMERA_DEVICE_IDX : ${CAMERA_DEVICE_IDX}
CAMERA_DEVICE_PATH: ${CAMERA_DEVICE_PATH}

ID_VENDOR_ARRAY   :
${ID_VENDOR_ARRAY}
ID_PRODUCTS_ARRAY :
${ID_PRODUCT_ARRAY}

FIRST_ID_VENDOR   : ${FIRST_ID_VENDOR}
FIRST_ID_PRODUCT  : ${FIRST_ID_PRODUCT}


SELECTED_ID_VENDOR  : [${SELECTED_ID_VENDOR}]
SELECTED_ID_PRODUCT : [${SELECTED_ID_PRODUCT}]
"


printf "
==============================================
RUNNING '__setup/05_configure_usb_udev_rule.sh'
"

#IDVENDOR=$1             # Vendor ID
#IDPRODUCT=$2            # Product ID
##SYMLINK=$3              # Symlink
SYMLINK=cams/usb



export camera_index=0
export camera_SYMLINK=${SYMLINK}

export camera_MODE=0664
export camera_GROUP=video
export camera_settings_file_path=/etc/udev/rules.d/99-cam.rules

echo "SUBSYSTEM==\"video4linux\", ATTRS{idVendor}==\"${SELECTED_ID_VENDOR}\", ATTRS{idProduct}==\"${SELECTED_ID_PRODUCT}\", ATTR{index}==\"${camera_index}\", MODE=\"${camera_MODE}\", GROUP=\"${camera_GROUP}\", SYMLINK+=\"${camera_SYMLINK}\"" > ${camera_settings_file_path}


printf "
==============================================
Symlink created: '${camera_SYMLINK}
"