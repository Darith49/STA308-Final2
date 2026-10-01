FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn

# Copy project files
COPY . /app/

# Expose port
EXPOSE 8000

# Default entrypoint runs migrations, static collection, and starts server
CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_demo && python manage.py runserver 0.0.0.0:8000"]
