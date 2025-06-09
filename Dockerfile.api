FROM python:3.12.3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements_docker.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements_docker.txt

COPY . .

# Copy the entrypoint script
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000

# Use the custom entrypoint
CMD ["/start.sh"]
