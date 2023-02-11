FROM python:3.9.1-slim-buster as shuffle

RUN apt-get update && apt-get install -y \
    ffmpeg

COPY requirements /app/requirements
RUN pip install -r /app/requirements/requirements.txt

COPY bot.py /app/bot.py
COPY shuffle /app/shuffle
COPY .env /app/.env

WORKDIR /app

CMD ["python", "bot.py"]
