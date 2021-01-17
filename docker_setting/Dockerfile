FROM python:3.8-alpine

WORKDIR /opt/

ENV LC_CTYPE='C.UTF-8'
ENV TZ='Asia/Tokyo'
ENV DEBIAN_FRONTEND=noninteractive

RUN set -x && \
    apk add --no-cache build-base nano git tzdata ncdu && \
    cp /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    python3 -m pip install -U setuptools && \
    git clone https://github.com/being24/sagumo.git && \
    python3 -m pip install -r ./sagumo/docker_setting/requirements.txt && \
    chmod 0700 ./sagumo/*.sh && \
    chmod 0700 ./sagumo/bot.py && \
    apk del build-base  && \
    rm -rf /var/cache/apk/*  && \
    echo "Hello, sagumo ready!" 

CMD ["/opt/sagumo/bot.sh"]