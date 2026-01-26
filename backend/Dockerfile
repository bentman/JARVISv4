# -------- Whisper.cpp build stage --------
FROM debian:stable-slim AS whisper_builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN git clone https://github.com/ggerganov/whisper.cpp.git
WORKDIR /opt/whisper.cpp
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j

# -------- llama.cpp build stage --------
FROM debian:stable-slim AS llama_builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN git clone https://github.com/ggerganov/llama.cpp.git
WORKDIR /opt/llama.cpp
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF \
 && cmake --build build -j

# -------- Piper TTS build stage --------
FROM debian:stable-slim AS piper_builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN git clone https://github.com/rhasspy/piper.git
WORKDIR /opt/piper
# Build Piper C++ inference engine
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j

# -------- Production runtime stage --------
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app
ENV PYTHONPATH="${APP_HOME}"
ENV LD_LIBRARY_PATH="/usr/local/lib:/opt/whisper/bin:/opt/whisper/lib:/opt/whisper/src:/opt/llama/lib:/opt/llama/bin:/opt/piper_build/pi/lib:/usr/local/bin:${LD_LIBRARY_PATH}"

# Set work directory
WORKDIR ${APP_HOME}

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        build-essential \
        libffi-dev \
        libssl-dev \
        curl \
        wget \
        libsndfile1 \
        espeak-ng \
        espeak-ng-data \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy AI model executables and libraries from build stages
COPY --from=whisper_builder /opt/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper
COPY --from=whisper_builder /opt/whisper.cpp/build/*.so* /usr/local/lib/
COPY --from=whisper_builder /opt/whisper.cpp/build/ /opt/whisper/

COPY --from=llama_builder /opt/llama.cpp/build/bin/ /usr/local/bin/
COPY --from=llama_builder /opt/llama.cpp/build/ /opt/llama/

COPY --from=piper_builder /opt/piper/build/piper /usr/local/bin/piper
COPY --from=piper_builder /opt/piper/build/ /opt/piper_build/

# Create necessary directories with proper permissions
RUN mkdir -p /app /app/data /app/logs /models \
    && chown -R appuser:appuser /app /models

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Copy project with proper ownership
COPY --chown=appuser:appuser . /app/backend

# Switch to non-root user
USER appuser

# Image metadata labels
LABEL com.jarvis.project="JARVISv4" \
      com.jarvis.service="backend" \
      com.jarvis.variant="prod"

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]