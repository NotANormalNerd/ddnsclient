FROM python:3.10-alpine as developement
WORKDIR /srv/

COPY ddnsclient ./ddnsclient
COPY setup.cfg pyproject.toml ./

RUN ls -al && pip install .