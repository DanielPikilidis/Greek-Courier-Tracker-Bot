FROM python:3.10

RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
  gnupg \
    --no-install-recommends \
    && curl -sSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y \
    google-chrome-stable \
    --no-install-recommends

# It won't run from the root user.
RUN groupadd chrome && useradd -g chrome -s /bin/bash -G audio,video chrome \
    && mkdir -p /home/chrome && chown -R chrome:chrome /home/chrome

ADD requirements.txt .
RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt

ADD cogs/* cogs/
ADD bot.py .

CMD ["python3", "bot.py"]