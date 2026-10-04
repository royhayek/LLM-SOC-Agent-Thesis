FROM python:3.12.11-slim-bookworm

RUN pip install --no-cache-dir nfstream==6.6.0

COPY capture.py /app/capture.py
WORKDIR /app
CMD ["python", "-u", "capture.py"]
