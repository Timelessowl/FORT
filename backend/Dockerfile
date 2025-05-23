FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./backend/requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install --upgrade torch sentence-transformers langchain-huggingface transformers
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')"

COPY ./backend/ /app/

COPY .env /app/

COPY ./backend/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

