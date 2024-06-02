FROM python:3.12.3-alpine as builder

RUN apk update && \
    apk upgrade && \
    apk add --no-cache python3-dev build-base && \
    pip3 install --upgrade pip

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip3 install -r requirements.txt

FROM python:3.12.3-alpine

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /bot
COPY /src/* /bot/

CMD ["python3", "main.py"]