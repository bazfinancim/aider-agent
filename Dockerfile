FROM python:3.11-slim

RUN pip install aider-chat

WORKDIR /app

COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
