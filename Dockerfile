FROM python:3.9-slim-buster

WORKDIR /app

# Upgrade pip (important)
RUN python3 -m pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "main.py"]
