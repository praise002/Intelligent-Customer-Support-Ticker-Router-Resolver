ifneq (,$(wildcard ./.env))
include .env
export 
ENV_FILE_PARAM = --env-file .env

endif

build:
	docker compose up --build -d --remove-orphans

up_build:
	docker compose -f docker-compose.dev.yml up --build 

up:
	docker compose up 

up_d:
	docker compose up -d

up_f:
	docker compose -f docker-compose.dev.yml up 

down:
	docker compose down

down_f:
	docker compose -f docker-compose.dev.yml down

show_logs:
	docker compose logs

serv:
	uvicorn src:app --reload

create_env:
	python3.12 -m venv venv

reqn:
	pip install -r requirements.txt

ureqn:
	pip freeze > requirements.txt

alembic_init:
	alembic init -t async migrations

mmig: 
	if [ -z "$(message)" ]; then \
		alembic revision --autogenerate; \
	else \
		alembic revision --autogenerate -m "$(message)"; \
	fi

mmig_auto:
	alembic revision --autogenerate
	
mig:
	alembic upgrade head

tests:
	pytest --disable-warnings -vv -x -s

random_s:
	python3 -c "import secrets; print(secrets.token_urlsafe(32))"

ngrok:
	ngrok http 7000

celery:
	celery -A src.tickets.celery_config.celery_app worker --loglevel=info --concurrency=3 -Q classification,processing

celery-beat:
	celery -A src.tickets.celery_config.celery_app beat --loglevel=info

redis:
	docker run --name redis -p 6379:6379 redis

redis_d:
	docker run -d --name redis -p 6379:6379 redis


# sudo systemctl restart docker
# 	source venv/bin/activate
# docker compose -f docker-compose.dev.yml web logs 
# docker compose -f docker-compose.dev.yml up  --force-recreate
# docker compose -f docker-compose.dev.yml up  --force-recreate web
# docker compose -f docker-compose.dev.yml up --build --force-recreate web
# docker compose -f docker-compose.dev.yml restart celery
# docker exec -it container_id sh
# docker exec -it 814d267be2aa sh
# cat /app/src/tickets/tasks.py
# docker run -it --rm -v $(pwd):/app backend-celery-1 python -c "from src.tickets.celery_config import celery_app"