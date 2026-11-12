# Dependencies only. The code under test is mounted fresh for every attempt.
FROM python:3.12-slim
RUN pip install --no-cache-dir numpy pandas packaging pytest hypothesis
RUN useradd -m -u 1000 runner
WORKDIR /work
