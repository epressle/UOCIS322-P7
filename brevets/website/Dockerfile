FROM python:3.8
LABEL maintainer="epressle@uoregon.edu"
RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential
COPY . /website
WORKDIR /website
RUN pip install -r requirements.txt
