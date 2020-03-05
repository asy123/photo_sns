FROM python:3.7

RUN pip3 install pipenv

RUN mkdir /opt/web
WORKDIR /opt/web

COPY Pipfile /opt/web/Pipfile
RUN pipenv install --deploy --skip-lock --system

COPY uwsgi.ini /opt/web/uwsgi.ini

COPY app /opt/web/app

RUN groupadd -r web && useradd -r -g web web
USER web

CMD ["python3"]