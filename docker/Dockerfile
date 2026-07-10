# loxcode bridge
# Build (aus loxcode-bridge/):  docker build -f docker/Dockerfile -t loxcode-bridge .
FROM python:3.14-slim
WORKDIR /app
COPY bridge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bridge/ .
# GPL: Lizenz reist mit dem Image (loxcode-bridge/LICENSE liegt im Build-Kontext)
COPY LICENSE /app/LICENSE
RUN useradd -r bridge
USER bridge
EXPOSE 5000
HEALTHCHECK --interval=60s --timeout=5s \
  CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "app:application"]
