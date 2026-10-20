FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Najpierw zależności: ta warstwa jest cache'owana, dopóki requirements.txt się nie zmieni.
# Dependencies first. This layer is cached until the requirements.txt file change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY eval ./eval

# Aplikacja nie musi działać jako root.
# The app does not have to work as a root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
