FROM naisy/donkeycar-pc:overdrive4

MAINTAINER Letenkov Maksim <letenkovmaksim@yandex.ru>

SHELL ["/bin/bash", "-c"]



#WORKDIR /
#RUN sudo git clone https://github.com/autorope/donkeycar
#WORKDIR /donkeycar
#RUN sudo git checkout main
#RUN sudo chmod 777 -R .
#RUN source ~/.virtualenv/donkeycar4/bin/activate
#RUN pip3 install -e .[pc]


WORKDIR /home/ubuntu/projects
RUN sudo rm -r donkeycar
RUN sudo git clone https://github.com/autorope/donkeycar
WORKDIR /home/ubuntu/projects/donkeycar
RUN sudo git checkout main
RUN sudo chmod 777 -R .
RUN source ~/.virtualenv/donkeycar4/bin/activate
# RUN pip3 install -e .[pc]

RUN pip3 install pyserial \
                pillow \
                docopt \
                tornado \
                requests \
                paho-mqtt \
                simple_pid \
                progress \
                typing_extensions \
                pyfiglet \
                psutil \
                pynmea2 \
                utm
RUN pip3 install git+https://github.com/autorope/keras-vis.git
RUN sudo apt update
RUN sudo apt install -y alsa-utils
RUN sudo apt install -y pulseaudio
RUN sudo apt-get install libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev -y \
        && pip3 install pyaudio

#RUN pip3 install --no-deps .[pc]
RUN pip3 install -e .[pc]

RUN echo "cd /home/ubuntu/donkey_car" >> /home/ubuntu/.bashrc
WORKDIR /home/ubuntu/donkey_car
CMD [ "bash" ]
