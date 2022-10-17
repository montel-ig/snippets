FROM python:3.8-slim-buster
MAINTAINER arslan@montel.fi

ENV PYTHONUNBUFFERED 1
ENV WORK_DIR /app
RUN mkdir -p ${WORK_DIR}

WORKDIR ${WORK_DIR}

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install requests dnspython && \
    rm -rf ~/.cache/pip /tmp/pip-build-root

# clean up a bit
RUN apt-get -y clean
