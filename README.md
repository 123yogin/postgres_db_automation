# PostgreSQL Automation

Scripts to automate PostgreSQL tasks on WSL, containerised with Docker.

## What's included

- **`psql_wsl.py`** — Python helper for running PostgreSQL operations under WSL (psycopg2)
- **`wsl_setup.sh`** — set up the WSL/PostgreSQL environment
- **`Dockerfile`** — containerised runtime
- **`.env.example`** — connection settings template

## Usage

```bash
cp .env.example .env         # set the PostgreSQL connection details
bash wsl_setup.sh            # one-time environment setup

pip install -r requirements.txt
python3 psql_wsl.py

# or via Docker
docker build -t postgres-automation .
docker run --rm --env-file .env postgres-automation
```

## Tech stack

- Python (psycopg2, python-dotenv)
- Docker, WSL
