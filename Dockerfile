FROM python:3.11-slim

RUN pip install aider-chat flask gunicorn

WORKDIR /app

COPY server.py .
COPY requirements.txt .

EXPOSE 10000

CMD ["python", "server.py"]
