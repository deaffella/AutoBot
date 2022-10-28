## Jetpack 4.6.2 [L4T 32.7.2]
## opencv     =   4.5.0
## tensorflow =   1.15.5
## pytorch    =   1.10.0
#FROM nvcr.io/nvidia/l4t-ml:r32.7.1-py3

# Jetpack 4.6.2 [L4T 32.7.2]
# opencv     =   --- -> 4.5.0
# tensorflow =   2.7
# pytorch    =   ---
FROM nvcr.io/nvidia/l4t-tensorflow:r32.7.1-tf2.7-py3

MAINTAINER Letenkov Maksim <letenkovmaksim@yandex.ru>


SHELL ["/bin/bash", "-c"]


# pytorch install
# https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048


RUN apt update
RUN apt install -y build-essential pkg-config
RUN apt install -y curl wget git nano dos2unix net-tools


# install OpenCV (with CUDA)
# note:  do this after numba, because this installs TBB and numba complains about old TBB
#
ARG OPENCV_URL=https://nvidia.box.com/shared/static/5v89u6g5rb62fpz4lh0rz531ajo2t5ef.gz
ARG OPENCV_DEB=OpenCV-4.5.0-aarch64.tar.gz

RUN mkdir opencv && \
    cd opencv && \
    wget --quiet --show-progress --progress=bar:force:noscroll --no-check-certificate ${OPENCV_URL} -O ${OPENCV_DEB} && \
    tar -xzvf ${OPENCV_DEB} && \
    dpkg -i --force-depends *.deb && \
    apt-get update && \
    apt-get install -y -f --no-install-recommends && \
    dpkg -i *.deb && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    cd ../ && \
    rm -rf opencv

RUN apt update
RUN apt install -y zlib1g-dev libfreetype6-dev
RUN apt install -y libevent-dev libbsd-dev v4l-utils imagemagick libv4l-dev uvcdynctrl
RUN apt-get -y install libavformat-dev \
                       libavutil-dev \
                       libavcodec-dev \
                       liblivemedia-dev \
                       xxd

RUN apt-get upgrade -y

RUN apt-get install -y zip libjpeg8-dev liblapack-dev libblas-dev gfortran
RUN apt-get install -y python3-dev python3-pip
RUN apt-get install -y libhdf5-serial-dev hdf5-tools libhdf5-dev
RUN apt-get install -y libxslt1-dev libxml2-dev libffi-dev libcurl4-openssl-dev libssl-dev libpng-dev libopenblas-dev
RUN apt-get install -y openmpi-doc openmpi-bin libopenmpi-dev libopenblas-dev
RUN apt-get install -y libjpeg-dev libpython3-dev libswscale-dev



RUN python3 -m pip install --upgrade pip
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install cpython
RUN pip3 install tqdm tabulate

RUN pip3 install imutils
RUN python3 -m pip install --upgrade Pillow

RUN pip3 install pip testresources
RUN pip3 install cython pyserial


## CuPy
##
#ARG CUPY_VERSION=v9.2.0
#ARG CUPY_NVCC_GENERATE_nano CODE="arch=compute_53,code=sm_53;arch=compute_62,code=sm_62;arch=compute_72,code=sm_72"
#
#RUN git clone -b ${CUPY_VERSION} --recursive https://github.com/cupy/cupy cupy && \
#    cd cupy && \
#    pip3 install fastrlock && \
#    python3 setup.py install --verbose && \
#    cd ../ && \
#    rm -rf cupy


RUN apt update
RUN apt install -y v4l2loopback-utils ffmpeg
RUN pip3 install pyzmq imagezmq
RUN pip3 install pyfakewebcam

RUN apt install -y gcc cmake

WORKDIR /
RUN mkdir temp_dir

# SIMPLEJPEG
WORKDIR /temp_dir
RUN git clone https://gitlab.com/jfolz/simplejpeg
WORKDIR /temp_dir/simplejpeg/
RUN python3 setup.py bdist_wheel
RUN python3 setup.py install


RUN apt install -y libssl1.0-dev
RUN apt install -y nodejs nodejs-dev
RUN apt install -y node-gyp
RUN apt install -y npm
RUN pip3 install jupyter jupyterlab

#RUN npm cache clean -f
#RUN npm install -g n
#RUN n latest
#RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager

RUN jupyter lab --generate-config


WORKDIR /
CMD [ "bash" ]