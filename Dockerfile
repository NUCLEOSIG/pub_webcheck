FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Exponer el puerto de Flask
EXPOSE 5000

# El comando se define en docker-compose, pero dejamos uno por defecto
CMD ["python", "app.py"]