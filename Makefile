.PHONY: test smoke manifest paper-check check release-check package-check

test:
	PYTHONPATH=src python -m pytest -q

smoke:
	PYTHONPATH=src python -m notreks.cli smoke

manifest:
	PYTHONPATH=src python -m notreks.manifest artifacts/protocol_manifest.json

paper-check:
	PYTHONPATH=src python -m notreks.paper_outputs --check

check: test smoke

release-check: check
	@PYTHONPATH=src python -m notreks.release . >/dev/null
	@find data/external/causalman/canonical data/external/causalassembly/canonical \
	  -name manifest.json -exec sh -c \
	  'for manifest do PYTHONPATH=src python -m notreks.external "$$manifest" >/dev/null || exit; done' \
	  sh {} +
	@echo "release check passed"

package-check:
	@python -m pip wheel --no-deps --no-build-isolation . --wheel-dir /tmp/notreks-wheel
