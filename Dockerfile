FROM python:3.10-alpine

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN pip install pipenv && pipenv install --system --deploy