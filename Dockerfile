FROM python:3.9-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# Expose Hugging Face's default port 7860
EXPOSE 7860

# Adjust this line to point to the main file that starts your app
CMD ["python", "main.py"]