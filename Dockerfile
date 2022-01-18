FROM python:3

ADD cogs/* cogs/
ADD bot.py .
ADD requirements.txt .

RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python3", "bot.py"]