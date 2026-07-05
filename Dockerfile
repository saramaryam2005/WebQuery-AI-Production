# 1. Official Python Slim base container utilization
FROM python:3.11-slim

WORKDIR /code

# 2. Layer caching for installation tracking
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 3. Code delivery context
COPY . /code

# 4. Open general security permission write profiles for vector caches
RUN chmod -R 777 /code

# 5. Hugging Face network binding interface
EXPOSE 7860

# 6. Execute direct production server orchestration standard 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]