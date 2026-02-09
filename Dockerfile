FROM python:3.11-slim

WORKDIR /app

# systémové balíčky (PDF, lxml, zip atď.)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Projekt
COPY . .

# Dátové adresáre
RUN mkdir -p data/xml data/tmp_pdf data/tmp_txt

ENV PYTHONUNBUFFERED=1

CMD ["bash"]
