FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY core-banking-mock/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY core-banking-mock/app/ /app/app/

EXPOSE 8500
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500"]
