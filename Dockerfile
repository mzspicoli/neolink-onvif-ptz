FROM python:3.12-slim
RUN pip install --no-cache-dir aiohttp==3.12.15 lxml==6.0.2
WORKDIR /app
COPY bridge /app/bridge
ENV CAMERA_NAME=camera LISTEN_HOST=127.0.0.1 LISTEN_PORT=8765 NEOLINK_URL=http://127.0.0.1:8655
CMD ["python", "-m", "bridge.main"]
