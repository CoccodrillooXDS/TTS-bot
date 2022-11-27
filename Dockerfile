FROM python:3.10-bullseye
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt upgrade -y
RUN apt install -y ffmpeg git libffi-dev
RUN mkdir app
WORKDIR /app
RUN git clone https://github.com/CoccodrillooXDS/TTS-bot.git .
RUN mkdir configs
RUN pip3 install -r requirements.txt

ENTRYPOINT [ "python3", "-u", "bot.py" ]