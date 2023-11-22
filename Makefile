TEST_PATH = ""

migrations:
	cd test_project && python manage.py makemigrations
init:
	cd test_project && python manage.py migrate && python manage.py loaddata fixtures/test_data.json
run:
	cd test_project && python manage.py runserver 0.0.0.0:8000
lint:
	black mailinglist
	isort mailinglist
	cd mailinglist && pflake8
test:
	pytest --cov=mailinglist --cov-report term-missing tests/$(TEST_PATH)