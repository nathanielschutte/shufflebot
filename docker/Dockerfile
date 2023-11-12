FROM python:3.9.1-slim-buster as shuffle

RUN apt-get update && apt-get install -y \
    ffmpeg

RUN mkdir -p /var/log/shuffle
RUN mkdir -p /var/lib/shuffle

COPY lib /app/lib
COPY requirements /app/requirements
RUN pip install -r /app/requirements/requirements-docker.txt

COPY bot.py /app/bot.py
COPY shuffle /app/shuffle
COPY .env /app/.env
COPY config /app/config
COPY docker/docker-entrypoint.sh /app/docker-entrypoint.sh

WORKDIR /app

ENTRYPOINT [ "sh", "docker-entrypoint.sh" ]

CMD ["python", "bot.py"]
