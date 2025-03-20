FROM python:3.13.2

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8000


