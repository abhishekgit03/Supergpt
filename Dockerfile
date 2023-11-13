FROM python:3.10

WORKDIR /app

COPY requirements.txt requirements.txt

RUN python3 -m pip install --upgrade pip setuptools
RUN python3 -m pip install --upgrade -r requirements.txt
# RUN python3 requirements.py

ARG PORT=8080
ARG TIMEOUT=3000
ARG WORKERS=1
ARG THREADS=1
ENV PROD=0

COPY . .

EXPOSE $PORT
CMD python3 app.py
