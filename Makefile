.PHONY: demo test dashboard

demo:
	python run.py all

test:
	python -m pytest -q

dashboard:
	python run.py report
