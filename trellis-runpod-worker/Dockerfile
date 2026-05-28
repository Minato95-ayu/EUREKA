# Use an official PyTorch + CUDA image as base
FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime

# Set working directory
WORKDIR /app

# Install system dependencies (required for 3D processing and git)
RUN apt-get update && apt-get install -y \
    git \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone the TRELLIS repository (or copy local files if you modified it)
# Note: Adjust the repo link to the specific official TRELLIS repo you are using
RUN git clone https://github.com/microsoft/TRELLIS.git .

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the heavy model weights to bake them into the Docker image
# This prevents downloading 10GB+ every time the serverless pod wakes up
RUN python -c "from trellis.pipelines import TrellisImageTo3DPipeline; TrellisImageTo3DPipeline.from_pretrained('JeffreyXiang/TRELLIS-image-large')"

# Copy the RunPod serverless handler and startup script
COPY handler.py .
COPY start.sh .

# Make the start script executable
RUN chmod +x start.sh

# Start the RunPod worker
CMD ["./start.sh"]
