FROM python:3.11

EXPOSE 5000

WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app
COPY db_handler.py /app

CMD ["python", "app.py"]