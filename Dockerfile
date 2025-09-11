FROM python:3.12

WORKDIR /myflask

COPY requirments.txt .

RUN pip install --no-cache-dir -r requirments.txt

COPY . .

ENV FLASK_RUN_HOST=0.0.0.0

CMD [ "flask","app","--host=0.0.0.0","--port=5000" ]
