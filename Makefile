.PHONY: test smoke manifest check release-check

test:
	PYTHONPATH=src python -m pytest -q

smoke:
	PYTHONPATH=src python -m notreks.cli smoke

manifest:
	PYTHONPATH=src python -m notreks.manifest artifacts/protocol_manifest.json

check: test smoke

release-check: check
	@set -e; \
	find data/external/causalman/canonical data/external/causalassembly/canonical \
	  -name manifest.json -print0 | \
	  while IFS= read -r -d '' manifest; do \
	    PYTHONPATH=src python -m notreks.external "$$manifest" >/dev/null; \
	  done
	@echo "release check passed"
