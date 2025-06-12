# Use Python 3.12.3 base image
FROM python:3.12.3-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /code

# Only copy the requirements file first (cache-friendly)
COPY requirements_docker.txt .

# Install dependencies (cached unless the requirements file changes)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements_docker.txt

# Now copy the rest of your code
COPY . .

# Expose port
EXPOSE 8000

# Run the app
CMD ["fastapi", "dev", "main.py", "--host", "0.0.0.0", "--port", "8000"]