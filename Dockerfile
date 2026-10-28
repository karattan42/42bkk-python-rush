# Streakr web view for Dokploy (or any Docker host). Standard library only, so no pip install.
FROM python:3.12-slim

WORKDIR /app
COPY *.py ./

# HOST=0.0.0.0 so the proxy in front of the container can reach the server.
# The database lives in /data: mount a volume there so accounts survive redeploys.
# Set ALLOWED_HOSTS to your domain in Dokploy, e.g. streakr.example.com
# TZ: "today" and streaks follow Thai time, not the server's UTC clock.
ENV HOST=0.0.0.0 \
    PORT=8042 \
    STREAKR_DB=/data/gym.db \
    TZ=Asia/Bangkok \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# Run as a normal user, not root.
# Same user id (10001) as the SSH container, so both can write the shared database.
RUN useradd --uid 10001 --no-create-home streakr && mkdir /data && chown streakr /data
USER streakr
VOLUME /data

EXPOSE 8042
CMD ["python", "server.py"]
