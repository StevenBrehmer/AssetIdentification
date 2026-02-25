FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    fonts-dejavu-core \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install GroundingDINO (adds capability; doesn't touch your app code)
RUN git clone --depth 1 https://github.com/IDEA-Research/GroundingDINO.git /opt/GroundingDINO \
  && pip install --no-cache-dir -e /opt/GroundingDINO

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]