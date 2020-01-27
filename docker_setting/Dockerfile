FROM ubuntu:18.04

WORKDIR /opt/

ENV LC_CTYPE='C.UTF-8'
ENV TZ='Asia/Tokyo'
ENV DEBIAN_FRONTEND=noninteractive

COPY token /opt

RUN set -x && \
    apt-get update && \
    apt-get install -y --no-install-recommends python3.7 python3-pip nano git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    cp /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    pip3 install -U setuptools && \
    git clone https://github.com/being24/sagumo.git && \
    pip3 install -r ./sagumo/docker_setting/requirements.txt && \
    chmod 0700 ./sagumo/*.sh && \
    mv /opt/token /opt/sagumo && \
    echo "Hello, sagumo ready!"

CMD ["/opt/sagumo/bot.sh"]