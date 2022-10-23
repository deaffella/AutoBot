## Jetpack 4.6.2 [L4T 32.7.2]
## opencv     =   --- -> 4.5.0
## tensorflow =   2.7
## pytorch    =   ---
#FROM nvcr.io/nvidia/l4t-tensorflow:r32.7.1-tf2.7-py3
FROM autobot:l4t_cv_tf

MAINTAINER Letenkov Maksim <letenkovmaksim@yandex.ru>


SHELL ["/bin/bash", "-c"]

RUN apt update
RUN apt install -y v4l2loopback-utils ffmpeg




RUN pip3 install pyzmq imagezmq
RUN pip3 install pyfakewebcam



# install donkeycar
#
#RUN pip3 install futures==3.1.1 protobuf==3.12.2 pybind11==2.5.0
RUN pip3 install futures==3.1.1 pybind11==2.5.0
#RUN pip3 install cython==0.29.21
RUN pip3 install future==0.18.2 mock==4.0.2 h5py==2.10.0 keras_preprocessing==1.1.2 keras_applications==1.0.8 gast==0.3.3
RUN pip3 install absl-py==0.9.0 py-cpuinfo==7.0.0 psutil==5.7.2 portpicker==1.3.1 six requests==2.24.0 astor==0.8.1 termcolor==1.1.0 wrapt==1.12.1 google-pasta==0.2.0
RUN pip3 install gdown


WORKDIR /
RUN git clone https://github.com/autorope/donkeycar
WORKDIR /donkeycar
RUN git checkout main
RUN pip3 install -e .[nano]

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


WORKDIR /donkey_car/
CMD [ "bash" ]
