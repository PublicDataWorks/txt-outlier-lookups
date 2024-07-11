FROM python:3.12-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y gdal-bin libgdal-dev postgresql-client

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "main:app"]
