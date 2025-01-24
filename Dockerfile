FROM python:3.12-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y gdal-bin libgdal-dev postgresql-client
RUN wget -O jq https://github.com/jqlang/jq/releases/download/jq-1.5/jq-linux64 && chmod +x ./jq && cp jq /usr/bin

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "10", "--timeout", "300", "--bind", "0.0.0.0:5000", "main:app"]
