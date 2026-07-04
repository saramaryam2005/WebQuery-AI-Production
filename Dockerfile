# UPGRADED TO PYTHON 3.11
FROM python:3.11-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code
RUN chmod -R 777 /code

CMD ["python", "app/main.py"]