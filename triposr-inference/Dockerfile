FROM pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone TripoSR repository for the model architecture
RUN git clone https://github.com/VAST-AI-Research/TripoSR.git /app/TripoSR

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add TripoSR path
ENV PYTHONPATH="/app/TripoSR:${PYTHONPATH}"

COPY app.py .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
