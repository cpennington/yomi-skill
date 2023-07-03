FROM python:3.10-slim

RUN apt-get update && apt-get -y install git build-essential libsnappy-dev automake libtool

WORKDIR /code

COPY requirements.txt /tmp

RUN --mount=type=cache,target=/root/.cache python -m pip install -r /tmp/requirements.txt
RUN ls /code
#RUN --mount=type=cache,target=/root/.cache python -m pip install /code/yomi_skill/
#RUN install_cmdstan

#EXPOSE 9999

#ENTRYPOINT ["jupyter-lab", "--ip=0.0.0.0", "--allow-root", "--port=9999"]
