# PostgreSQL Container Automation Dockerfile
FROM ubuntu:22.04

# Avoid interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install System Dependencies
# - python3: to run the script
# - xvfb: virtual display server
# - xfce4*: for a desktop-like environment (taskbars, windows)
# - xwininfo/xdotool: for window manipulation
# - scrot: for screenshots
# - postgresql-client: for psql command
# - rclone: for Google Drive upload
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-setuptools \
    xvfb \
    xfce4 \
    xfce4-terminal \
    xfwm4 \
    xdotool \
    scrot \
    postgresql-client \
    rclone \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies directly
# - psycopg2-binary: Postgres database adapter
# - python-dotenv: Load environment variables from .env
RUN pip3 install --no-cache-dir \
    psycopg2-binary \
    python-dotenv

# 3. Setup Working Directory
WORKDIR /app

# 4. Copy the script
COPY psql_wsl.py .

# 5. Set Environment Variables
ENV DISPLAY=:99
ENV OUTPUT_DIR=/app/output
ENV PYTHONUNBUFFERED=1

# 6. Create output directory
RUN mkdir -p /app/output

# 7. Start the automation script
CMD ["python3", "psql_wsl.py"]
