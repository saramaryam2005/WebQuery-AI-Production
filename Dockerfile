FROM python:3.9-slim

WORKDIR /code

# Copy requirements first to take advantage of Docker caching
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# CRITICAL: Copy all remaining project files (including main.py and folders) into the container
COPY . /code

# Set permissions so the container can access the files safely
RUN chmod -R 777 /code

# Command to run your application
CMD ["python", "main.py"]