FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libffi-dev \
      libcairo2 \
      libpango-1.0-0 \
      fonts-dejavu-core \
  && pip install --no-cache-dir -r requirements.txt \
  && apt-get purge -y build-essential libffi-dev \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/
COPY config.json .
COPY fonts/ /usr/share/fonts/truetype/montserrat/
RUN fc-cache -f -v

CMD ["python", "src/main.py"]
