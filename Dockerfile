FROM python:3.11.4-slim-bullseye

RUN mkdir /bot

COPY requirements.txt /bot

WORKDIR /bot

RUN apt-get update -y && apt upgrade -y && apt install sqlite3

RUN pip3 install -r requirements.txt

COPY src/cogs/* /bot/cogs
COPY src/*.py /bot

CMD ["python3", "bot.py"]