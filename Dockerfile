FROM debian:bookworm-slim

ARG PUID=1000
ARG PGID=1000
ENV USER=dmcompile

RUN dpkg --add-architecture i386; \
        apt-get update; \
        apt-get install -yqq --no-install-recommends --show-progress \
        gcc-multilib lib32stdc++6 zlib1g-dev:i386 libssl-dev:i386 pkg-config:i386 libstdc++6 libstdc++6:i386 \
        python3 python3-pip python3-setuptools \
        nano curl unzip

WORKDIR /app

COPY requirements.txt /app
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY compile.sh listener.py ./
COPY templates templates/

RUN groupadd --force -g ${PGID} ${USER} \
    && useradd -ms /bin/bash --no-log-init --no-user-group -g ${PGID} -u ${PUID} ${USER} \
    && mkdir /app/byond \
    && chown -R ${USER}:${USER} /app

USER ${USER}

ENTRYPOINT ["python3", "listener.py"]
