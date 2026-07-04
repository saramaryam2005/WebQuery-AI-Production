FROM python:3.9-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code
RUN chmod -R 777 /code

# CHANGE THIS LAST LINE TO:
CMD ["python", "app/main.py"]