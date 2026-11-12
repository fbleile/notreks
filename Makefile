.PHONY: test smoke manifest check

test:
	PYTHONPATH=src python -m pytest -q

smoke:
	PYTHONPATH=src python -m notreks.cli smoke

manifest:
	PYTHONPATH=src python -m notreks.manifest artifacts/protocol_manifest.json

check: test smoke
