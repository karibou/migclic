FROM ubuntu:xenial

RUN apt-get update

RUN apt install -y python3 python3-requests python3-pip git locales

RUN pip3 install google-api-python-client

RUN mkdir .credentials

COPY .credentials/contacts-python-migclic-update.json .credentials/contacts-python-migclic-update.json
COPY .credentials/calendar-python-migclic-update.json .credentials/calendar-python-migclic-update.json
COPY setvar setvar
RUN git clone https://github.com/karibou/migclic.git

RUN locale-gen fr_FR.UTF-8
ENV LANG fr_FR.UTF-8
ENV LANGUAGE fr_FR:fr
ENV LC_ALL fr_FR.UTF-8
