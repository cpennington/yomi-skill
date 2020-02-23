FROM python:3.7-slim-stretch

RUN apt-get update && apt-get -y install git build-essential libsnappy-dev automake libtool

RUN git clone --depth=1 https://github.com/gambitproject/gambit /src/gambit
RUN cd /src/gambit && aclocal && libtoolize && automake --add-missing && autoconf && ./configure && make && make install

WORKDIR /code

COPY requirements.txt /tmp

RUN pip install -U pip
RUN pip install -U pip-tools

RUN pip-sync /tmp/requirements.txt
RUN pip install -e /src/gambit/src/python

EXPOSE 9999

ENTRYPOINT ["jupyter-lab", "--ip=0.0.0.0", "--allow-root", "--port=9999"]
