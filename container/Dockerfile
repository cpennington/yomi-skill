FROM python:3.7-slim-stretch

RUN apt-get update && apt-get -y install git build-essential libsnappy-dev

WORKDIR /code

COPY requirements.txt /tmp

RUN pip install -U pip
RUN pip install -U pip-tools

RUN pip-sync /tmp/requirements.txt

EXPOSE 9999

ENTRYPOINT ["jupyter-lab", "--ip=0.0.0.0", "--allow-root", "--port=9999"]
