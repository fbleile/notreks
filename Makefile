.PHONY: test smoke manifest check release-check

test:
	PYTHONPATH=src python -m pytest -q

smoke:
	PYTHONPATH=src python -m notreks.cli smoke

manifest:
	PYTHONPATH=src python -m notreks.manifest artifacts/protocol_manifest.json

check: test smoke

release-check: check
	@find data/external/causalman/canonical data/external/causalassembly/canonical \
	  -name manifest.json -exec sh -c \
	  'for manifest do PYTHONPATH=src python -m notreks.external "$$manifest" >/dev/null || exit; done' \
	  sh {} +
	@echo "release check passed"
