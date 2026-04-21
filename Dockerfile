FROM python:3.11-slim

RUN apt-get update && apt-get install -y git curl && apt-get clean

RUN pip install --no-cache-dir aider-chat flask

WORKDIR /app

COPY server.py .

EXPOSE 10000

CMD ["python", "server.py"]
