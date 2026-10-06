# Testbed commands (ticket E0-07). Stop Ollama before `make up` on 16 GB (README, Resources).
#   make up     start the testbed; raw logs go to data/raw/<run_id>/
#               BENIGN_SEED=<n> and BENIGN_DURATION_S=<s> override the benign profile (E1-05)
#   make down   stop the testbed, merge the per-host pcaps, derive flows, keep the raw logs
#   make reset  remove the testbed's containers and volumes; raw logs on disk are kept

.PHONY: up down reset

RAW_DIR := data/raw
CURRENT := $(RAW_DIR)/.current_run
BENIGN_PROFILE := testbed/profiles/benign.yaml
CAPTURE_IMAGE := thesis-testbed-capture:e1-16
# One egress-only capture sidecar per traffic source (ADR-0009). Must list every capture-*
# service in docker-compose.yml (tests/test_capture.py checks this).
CAPTURES := capture-broker capture-mqtt-logger capture-honeypot capture-emulator-temp \
	capture-emulator-cam capture-emulator-hum capture-emulator-plug
# Every service that sends or receives traffic, stopped before the capture sidecars so their
# last packets (connection closes) are in the pcaps. Emulators stop before the MQTT logger so
# the logger receives every published message.
EMULATORS := emulator-temp emulator-cam emulator-hum emulator-plug
OTHER_SOURCES := mqtt-logger honeypot

up:
	@if [ -f $(CURRENT) ]; then echo "Run $$(cat $(CURRENT)) is still up. Run 'make down' first."; exit 1; fi
	@run_id=$$(date -u +%Y%m%dT%H%M%SZ); \
	run_dir=$(RAW_DIR)/$$run_id; \
	mkdir -p $$run_dir/mqtt $$run_dir/flows/hosts $$run_dir/honeypot; \
	touch $$run_dir/mqtt/mqtt.log $$run_dir/mqtt/broker.log $$run_dir/honeypot/cowrie.json; \
	uv run --quiet python -m thesis.testbed.benign plan $(BENIGN_PROFILE) $$run_dir/benign_plan \
	  $(if $(BENIGN_SEED),--seed $(BENIGN_SEED)) $(if $(BENIGN_DURATION_S),--duration-s $(BENIGN_DURATION_S)) \
	  || { echo "Could not write the benign plans."; rm -rf $$run_dir; exit 1; }; \
	chmod -R a+rwX $$run_dir; \
	echo $$run_id > $(CURRENT); \
	if RUN_DIR=./$$run_dir docker compose up -d --build --force-recreate --remove-orphans; then \
	  echo "Testbed up. Run $$run_id writes to $$run_dir"; \
	else \
	  rm -f $(CURRENT); echo "make up failed; run 'make reset' before retrying."; exit 1; \
	fi

down:
	@if [ ! -f $(CURRENT) ]; then echo "No run is up."; exit 0; fi
	@run_id=$$(cat $(CURRENT)); \
	export RUN_DIR=./$(RAW_DIR)/$$run_id; \
	running=$$(docker compose ps -q --status running $(CAPTURES) | wc -l | tr -d ' '); \
	if [ "$$running" -ne $(words $(CAPTURES)) ]; then \
	  echo "ERROR: only $$running of $(words $(CAPTURES)) capture sidecars are running, so the pcaps are incomplete."; exit 1; \
	fi; \
	docker compose stop $(EMULATORS) && \
	docker compose stop $(OTHER_SOURCES) && \
	docker compose stop $(CAPTURES) && \
	docker compose down && \
	docker run --rm --network none -v "$$(pwd)/$(RAW_DIR)/$$run_id/flows:/out" \
	  --entrypoint sh $(CAPTURE_IMAGE) -c 'sh merge.sh && python flows.py' && \
	rm -f $(CURRENT) && \
	echo "Testbed down. Raw logs in $(RAW_DIR)/$$run_id"

reset:
	docker compose down --volumes --remove-orphans
	rm -f $(CURRENT)
