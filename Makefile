PYTHON ?= python3

.PHONY: info verify reproduce export test
info:
	$(PYTHON) scripts/project.py info

verify:
	$(PYTHON) scripts/project.py verify

reproduce:
	$(PYTHON) scripts/project.py reproduce

export:
	$(PYTHON) scripts/project.py export

test:
	$(PYTHON) -m unittest discover -s tests -v
