FROM python:3.9-slim-bullseye AS shuffle

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    git \
    wget \
    pkg-config \
    yasm \
    libopus-dev \
    libmp3lame-dev \
    libvorbis-dev \
    && apt-get remove -y ffmpeg \
    && apt-get clean

RUN cd /tmp && \
    wget -O ffmpeg.tar.bz2 https://ffmpeg.org/releases/ffmpeg-4.4.tar.bz2 && \
    tar xjf ffmpeg.tar.bz2 && \
    cd ffmpeg-* && \
    ./configure \
      --disable-debug \
      --enable-small \
      --disable-ffplay \
      --disable-doc \
      --enable-openssl \
      --enable-protocol=https,http \
      --enable-libmp3lame \
      --enable-libopus \
      --enable-libvorbis \
      --enable-shared && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf ffmpeg* && \
    ldconfig

ENV MALLOC_ARENA_MAX=2
ENV LD_LIBRARY_PATH=/usr/local/lib

RUN echo "* soft nofile 1048576" >> /etc/security/limits.conf && \
    echo "* hard nofile 1048576" >> /etc/security/limits.conf

RUN mkdir -p /var/log/shuffle
RUN mkdir -p /var/lib/shuffle

COPY requirements /app/requirements
RUN pip install -r /app/requirements/requirements-docker.txt

# Remove these lines since we're removing selenium, undetected-chromedriver, pytube
# RUN pip install selenium undetected-chromedriver pytube

COPY bot.py /app/bot.py
COPY shuffle /app/shuffle
COPY .env /app/.env
COPY config /app/config
COPY docker/docker-entrypoint.sh /app/docker-entrypoint.sh

WORKDIR /app

ENTRYPOINT [ "sh", "docker-entrypoint.sh" ]

CMD ["python", "bot.py"]