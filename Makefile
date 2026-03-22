ifneq (,$(wildcard ./.env))
include .env
export 
ENV_FILE_PARAM = --env-file .env

endif

build:
	docker-compose up --build -d --remove-orphans

up:
	docker-compose up -d

down:
	docker-compose down

show_logs:
	docker-compose logs

serv:
	uvicorn src:app --reload

create_env:
	python3.12 -m venv venv

reqn:
	pip install -r requirements.txt

ureqn:
	pip freeze > requirements.txt

alembic_init:
	alembic init app/db/migrations

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
# Run all auth tests
# pytest tests/test_auth/ -v

# # Run only registration tests
# pytest tests/test_auth/test_register.py -v
# 	python -m uvicorn src:app --reload
#  	python3 -m venv .venv

# 	source venv/bin/activate

# # Run with coverage
# pytest tests/test_auth/test_register.py --cov=src.auth --cov-report=html
# which python
# uvicorn src:app --reload --port 3000

#TODO: REMOVE LATER

celery -A src.celery_tasks.c_app worker
celery -A src.celery_tasks.c_app flower
st run open_ai_specification --experimantal=openai1.3.1
st run open_ai_specification --checks all --experimantal=openai1.3.1

.\env\bin\activate  
alembic --help
alembic init -t async migrations
alembic revision --autogenerate -m "Updated ticket db"
alembic upgrade head
docker run -d --name redis -p 6379:6379 redis

fastapi dev main.py

uvicorn main:app --reload

uvicorn src:app --reload --port 8001

redis-server
redis-cli ping
# Should return: PONG
celery -A src.celery_app worker --loglevel=info --concurrency=3
# Production command
celery -A src.celery_app worker \
  --loglevel=info \
  --concurrency=3 \
  --max-tasks-per-child=1000 \
  --time-limit=300 \
  --autoscale=5,2

celery -A src.celery_app beat --loglevel=info
celery -A src.tickets.celery_config.celery_app flower --port=5555
# http://localhost:5555

# flowerconfig.py

# Broker URL
broker_url = 'redis://localhost:6379/0'

# Port
port = 5555

# Basic authentication
basic_auth = ['admin:secret123', 'user:password']

# URL prefix (if behind reverse proxy)
url_prefix = 'flower'

# Enable/disable features
enable_events = True
natural_time = True
tasks_columns = ['name', 'uuid', 'state', 'args', 'kwargs', 'result', 'received', 'started', 'runtime', 'worker']

celery -A src.celery_app flower --conf=flowerconfig.py

# {{agent.signature}}