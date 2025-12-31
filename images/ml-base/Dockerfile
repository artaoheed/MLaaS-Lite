FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# We don't need a CMD or ENTRYPOINT because Argo will inject the command.