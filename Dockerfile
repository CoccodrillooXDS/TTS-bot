FROM ubuntu:latest
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update
RUN apt install -y python3-pip ffmpeg git
RUN mkdir app
WORKDIR app
RUN git clone https://github.com/CoccodrillooXDS/TTS-bot.git .
RUN pip3 install -r requirements.txt

ENTRYPOINT [ "python3", "bot.py" ]