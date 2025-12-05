# 1. Usar una imagen base oficial de Python (ligera)
FROM python:3.11-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar el archivo de requerimientos primero para aprovechar el cache de Docker
COPY requirements.txt .

# 4. Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el resto del código de la aplicación al contenedor
COPY update.py .
COPY urls.txt .

# 6. Comando por defecto para ejecutar el script cuando el contenedor inicie
CMD ["python", "update.py"]