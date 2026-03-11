FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY . .

RUN uv sync

EXPOSE 8463

CMD ["uv", "run", "fakevine"]