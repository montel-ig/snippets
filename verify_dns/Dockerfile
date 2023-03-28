FROM python:3.8-slim-buster
MAINTAINER arslan@montel.fi

ENV PYTHONUNBUFFERED 1
ENV WORK_DIR /app
ADD . ${WORK_DIR}

WORKDIR ${WORK_DIR}

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl watch xterm && \
    rm -rf /var/lib/apt/lists/* && \
    export TERM=xterm

RUN pip install requests dnspython==2.2.1 && \
    rm -rf ~/.cache/pip /tmp/pip-build-root

# clean up a bit
RUN apt-get -y clean
RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/check_dns.py

CMD /usr/bin/watch --interval 900 --exec python check_dns.py www.google.com
