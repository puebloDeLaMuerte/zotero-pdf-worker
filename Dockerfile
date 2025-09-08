FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libffi-dev \
      libcairo2 \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libgdk-pixbuf-2.0-0 \
      shared-mime-info \
      fonts-dejavu-core \
      fonts-liberation \
      fonts-noto-core \
      pkg-config \
      python3-dev \
  && pip install --no-cache-dir -r requirements.txt \
  && apt-get purge -y build-essential libffi-dev \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/
COPY config.json .
COPY fonts/ /usr/share/fonts/truetype/montserrat/
RUN fc-cache -f -v

CMD ["python", "src/main.py"]
