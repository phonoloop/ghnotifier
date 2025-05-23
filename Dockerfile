# docker build --no-cache -t ghnotifier .
# docker run --rm -d ghnotifier

FROM python:3.11-slim

# Install dependencies
RUN pip install requests python-dotenv && apt-get update && apt-get install -y cron

# Copy files
COPY script.py /app/script.py
COPY crontab /etc/cron.d/mention-cron

# Set permissions
RUN chmod 0644 /etc/cron.d/mention-cron && \
  touch /var/log/cron.log

WORKDIR /app

# Run cron in foreground
CMD cron && tail -f /var/log/cron.log
