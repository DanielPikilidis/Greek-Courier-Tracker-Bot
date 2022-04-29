FROM python:3

ADD cogs/* cogs/
ADD bot.py .
ADD requirements.txt .

RUN echo "deb http://deb.debian.org/debian/ unstable main contrib non-free" >> /etc/apt/sources.list.d/debian.list
RUN apt-get update
RUN apt-get install -y --no-install-recommends firefox

RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python3", "bot.py"]