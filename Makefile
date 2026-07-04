# Detecto Makefile

VERSION := 1.6.1
DIST_NAME := detecto_$(VERSION)
DIST_DIR := dist
DIST_FILE := $(DIST_DIR)/$(DIST_NAME).zip

DIST_FILES := \
	detecto_cli.py \
	detecto.ini \
	regexp.csv \
	field.csv \
	suchmuster.csv \
	stopword_regexp.txt \
	stopword_field.txt \
	stopword_suchmuster.txt \
	pyproject.toml \
	Makefile \
	LICENSE \
	readme.md \
	changelog.md \
	firststeps.md \
	prompt_documentation.md

DIST_DIRS := \
	src/detecto \
	tests \
	suchmuster

DATA_DIR := src/detecto/data
DATA_FILES := \
	detecto.ini \
	regexp.csv \
	field.csv \
	suchmuster.csv \
	stopword_regexp.txt \
	stopword_field.txt \
	stopword_suchmuster.txt

SUCHMUSTER_FILES := \
	vornamen.csv nachnamen.csv orte.csv diagnosen.csv \
	sicherheitsbegriffe.csv verschlusssachen.csv sperrvermerke.csv

.PHONY: dist clean test lint datasync

# Sync pattern files into the package data dir (for pip install)
datasync:
	@mkdir -p $(DATA_DIR)/suchmuster
	@for f in $(DATA_FILES); do \
		cp "$$f" $(DATA_DIR)/ || { echo "FEHLER: datasync $$f"; exit 1; }; \
	done
	@for f in $(SUCHMUSTER_FILES); do \
		cp "suchmuster/$$f" $(DATA_DIR)/suchmuster/ || { echo "FEHLER: datasync suchmuster/$$f"; exit 1; }; \
	done
	@echo "datasync: Package-Daten aktualisiert ($(DATA_DIR))"

dist: clean datasync
	@echo "=== Building $(DIST_FILE) ==="
	@mkdir -p $(DIST_DIR)/$(DIST_NAME)
	@for f in $(DIST_FILES); do \
		if [ -f "$$f" ]; then \
			cp "$$f" $(DIST_DIR)/$(DIST_NAME)/ || { echo "FEHLER: cp $$f fehlgeschlagen"; exit 1; }; \
		else \
			echo "FEHLER: $$f fehlt"; exit 1; \
		fi; \
	done
	@for d in $(DIST_DIRS); do \
		mkdir -p $(DIST_DIR)/$(DIST_NAME)/$$d; \
		cp -r $$d/* $(DIST_DIR)/$(DIST_NAME)/$$d/ 2>/dev/null || true; \
	done
	@# Kopien duerfen nicht leer sein (0-Byte-Kopien durch fehlgeschlagene
	@# Reads landeten sonst still im Release-ZIP)
	@for f in $(DIST_FILES); do \
		test -s "$(DIST_DIR)/$(DIST_NAME)/$$f" || { echo "FEHLER: $$f ist leer im Dist"; exit 1; }; \
	done
	@touch $(DIST_DIR)/$(DIST_NAME)/tests/__init__.py
	@# Exclude backup/temp files
	@cd $(DIST_DIR) && zip -r $(DIST_NAME).zip $(DIST_NAME)/ \
		-x "*.pyc" "*__pycache__*" "*.DS_Store" "*/andere/*"
	@rm -rf $(DIST_DIR)/$(DIST_NAME)
	@# Finaler Check direkt im ZIP
	@unzip -p $(DIST_FILE) $(DIST_NAME)/detecto_cli.py | grep -q "detecto.cli" \
		|| { echo "FEHLER: detecto_cli.py im ZIP leer/defekt"; exit 1; }
	@echo "=== Done: $(DIST_FILE) ==="
	@echo "Size: $$(du -h $(DIST_FILE) | cut -f1)"

clean:
	@rm -rf $(DIST_DIR)
	@echo "dist/ cleaned"

test:
	PYTHONPATH=src python3 -m pytest tests/ -v

lint:
	PYTHONPATH=src python3 -m ruff check src/ tests/
