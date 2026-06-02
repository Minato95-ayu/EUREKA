FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV EUREKA_3D_HOST=0.0.0.0
ENV EUREKA_3D_PORT=8093
ENV EUREKA_3D_OUTPUT_ROOT=/app/generated

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/generated

EXPOSE 8093

CMD ["python", "run_api.py"]

