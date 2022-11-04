FROM python:3.10-alpine

ARG BOT_NAME="sagumo"

WORKDIR /opt/

# set environment variables
ENV LC_CTYPE='C.UTF-8'
ENV TZ='Asia/Tokyo'
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./ ${BOT_NAME}

RUN set -x && \
    apk add --no-cache build-base nano git tzdata ncdu && \
    cp /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    python3 -m pip install -U setuptools && \
    # git clone https://github.com/being24/${BOT_NAME}.git && \
    python3 -m pip install -r ./${BOT_NAME}/requirements.txt && \
    # pip install -U git+https://github.com/Rapptz/discord.py && \
    chmod 0700 ./${BOT_NAME}/bot.py && \
    apk del build-base  && \
    rm -rf /var/cache/apk/*  && \
    rm -rf ./requirements.txt && \
    echo "Hello, ${BOT_NAME} ready!"

CMD ["python3","/opt/sagumo/bot.py"]