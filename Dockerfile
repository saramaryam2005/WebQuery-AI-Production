# UPGRADED TO PYTHON 3.11
FROM python:3.11-slim

WORKDIR /code

# Copy requirements and install packages
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy everything into the working directory
COPY . /code

# Enforce open directory read/write access profiles for safe local SQLite caching
RUN mkdir -p /code/chroma_db && chmod -R 777 /code

# Hugging Face Spaces listens exclusively on port 7860
EXPOSE 7860

# Run Uvicorn directly to launch your live FastAPI web app interface framework
ENV RUNNING_ON_HF=true
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]