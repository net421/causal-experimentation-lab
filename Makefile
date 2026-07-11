PYTHON ?= python3
PYTHONPATH ?= src

.PHONY: install reproduce test check clean

install:
	$(PYTHON) -m pip install -e .

reproduce:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m causal_lab.cli --root .

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

check: test reproduce
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

clean:
	rm -rf build dist .coverage src/*.egg-info src/causal_experimentation_lab.egg-info
