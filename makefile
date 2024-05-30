IMG=myfundquest

preptest:
	pip install -U pytest

unittest:
	cd tests/unit && PYTHONPATH=$(shell pwd)/src pytest -s --log-cli-level=INFO

local:
	cd src && flask --app app.py --debug run  -p 5000 

localadmin:
	cd src && flask --app app_admin.py --debug run  -p 5001

localtaskapi:
	cd src && flask --app app_tasks.py --debug run  -p 5002


gunicorn:
	cd src && gunicorn app:app --bind "0.0.0.0:15000"

coverage:
	PYTHONPATH=$(shell pwd)/src pytest --cov=src  tests/unit 
	coverage report -m

celery:
	cd src && PYTHONPATH=$(shell pwd)/src celery -A tasks worker --loglevel=INFO        

build:
	docker build -t ${IMG} .