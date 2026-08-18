.PHONY: test secret-scan safety

test:
	python -m pytest
secret-scan:
	python scripts/secret_scan.py
safety:
	PYTHONPATH=src python -m across_edge.cli safety-check
