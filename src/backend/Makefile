env:
	if [ -z '$$(command -v pyenv)' ]; then echo "Please install pyenv to manage python version" &&  exit 1; fi
	pyenv install -s
	pyenv local

installdeps:
	if [ -n '$$(shell command -v poetry)' ]; then echo "Poetry already installed"; else python3 -m pip install poetry; fi;
	poetry install
	poetry config virtualenvs.in-project true

createmigrations:
	poetry run python manage.py makemigrations

install: installdeps createmigrations

keys:
ifeq ($(inline),true)
	openssl genrsa -out /tmp/jwt-key 4096 2>/dev/null && awk 'BEGIN {ORS="\\n"} {print}' /tmp/jwt-key && echo "\n\n"
	openssl rsa -in /tmp/jwt-key -pubout -out /tmp/jwt-key.pub 2>/dev/null && awk 'BEGIN {ORS="\\n"} {print}' /tmp/jwt-key.pub && echo "\n\n"
	openssl req -new -x509 -nodes -sha256 -days 365 -key /tmp/jwt-key -out /tmp/jwk.cert -subj "/CN=example.com" 2>/dev/null && awk 'BEGIN {ORS="\\n"} {print}' /tmp/jwk.cert && echo "\n\n"
	rm /tmp/jwt-key && rm /tmp/jwt-key.pub && rm /tmp/jwk.cert
else
	mkdir -pv keys 
	openssl genrsa -out keys/jwt-key 4096
	openssl rsa -in  keys/jwt-key -pubout > keys/jwt-key.pub
	openssl req -new -x509 -nodes -sha256 -days 365 -key keys/jwt-key -out keys/jwk.cert
endif

migrate:
	poetry run python manage.py migrate

dev:
	poetry run python manage.py runserver 8000 

run:
	# for any of the others, please don't use development setting in production
	export DJANGO_SETTINGS_MODULE='worker_backend.settings';\
	poetry run gunicorn worker_backend.wsgi:application --workers 4 -b 0.0.0.0:8000

shell:
	@echo 'Starting poetry shell. Press Ctrl-d to exit from the shell'
	poetry shell

worker-logs: 
	python -m celery -A worker_backend worker -l info --concurrency=4 --logfile=celery_worker.log

worker: 
	python -m celery -A impress.celery_app worker -l info --pool threads --concurrency=4

worker-beats: 
	python -m celery -A worker_backend beat -l info

flower: 
	python -m celery -A worker_backend flower --port=5555

terminal: 
	python manage.py shell

proto-generate:
	poetry run python manage.py generateproto
	$(eval LOCAL_PROTO_LIB_URL=$(shell grep LOCAL_PROTO_LIB_URL .make.env | sed 's/LOCAL_PROTO_LIB_URL=//'))
	$(eval PROTO_SUB_DIR=$(shell grep PROTO_SUB_DIR .make.env | sed 's/PROTO_SUB_DIR=//'))
	$(eval PROTO_TARGET_DIR=$(shell echo '$(LOCAL_PROTO_LIB_URL)/$(PROTO_SUB_DIR)'))
	echo "Copying .proto files to $(PROTO_TARGET_DIR)"
	mkdir -p $(PROTO_TARGET_DIR)
	rsync -zarv  --prune-empty-dirs --include "*/"  --include="*.proto" --exclude="*" ./api $(PROTO_TARGET_DIR)

proto-clean:
	$(eval LOCAL_PROTO_LIB_URL=$(shell grep LOCAL_PROTO_LIB_URL .make.env | sed 's/LOCAL_PROTO_LIB_URL=//'))
	$(eval PROTO_SUB_DIR=$(shell grep PROTO_SUB_DIR .make.env | sed 's/PROTO_SUB_DIR=//'))
	$(eval PROTO_TARGET_DIR=$(shell echo '$(LOCAL_PROTO_LIB_URL)/proto/$(PROTO_SUB_DIR)'))
	$(eval PYTHON_TARGET_DIR=$(shell echo '$(LOCAL_PROTO_LIB_URL)/python/$(PROTO_SUB_DIR)'))  # New line
	rm -rf $(PROTO_TARGET_DIR)
	rm -rf $(PYTHON_TARGET_DIR)

proto-generate-dev:
	@echo 'Warining: Do not push any files that are generated from this command'
	poetry run python manage.py generateproto

grpc-dev:
	python manage.py grpcrunaioserver 127.0.0.1:2000 --dev

grpc-prod:
	python manage.py grpcrunaioserver 127.0.0.1:5000 --max-workers 4
