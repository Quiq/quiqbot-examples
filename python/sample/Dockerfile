FROM quiq/python:3.6

WORKDIR /service

COPY sample.py config.py requirements.txt ./
RUN pip3 install -r requirements.txt

USER nobody
CMD ["gunicorn", "--bind", "0.0.0.0:9000", "sample:create_app()", "--access-logfile", "-"]
