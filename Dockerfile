FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libpq-dev \
    python3-dev \
    git \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install dlib
RUN pip install .

COPY . .

EXPOSE 8765

CMD ["python", "server/main.py", "--host", "0.0.0.0", "--port", "8765"]