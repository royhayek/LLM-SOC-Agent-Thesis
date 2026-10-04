# Testbed commands (ticket E0-07). Stop Ollama before `make up` on 16 GB (README, Resources).
#   make up     start the testbed; raw logs go to data/raw/<run_id>/
#   make down   stop the testbed, derive flows from the pcap, keep that run's raw logs
#   make reset  remove the testbed's containers and volumes; raw logs on disk are kept

.PHONY: up down reset

RAW_DIR := data/raw
CURRENT := $(RAW_DIR)/.current_run
CAPTURE_IMAGE := thesis-testbed-capture:e0-07
# Every service that sends or receives traffic, stopped before the capture so their last
# packets (connection closes) are in the pcap. Emulators stop before the MQTT logger so
# the logger receives every published message.
EMULATORS := emulator-temp emulator-cam emulator-hum emulator-plug
OTHER_SOURCES := mqtt-logger honeypot

up:
	@if [ -f $(CURRENT) ]; then echo "Run $$(cat $(CURRENT)) is still up. Run 'make down' first."; exit 1; fi
	@run_id=$$(date -u +%Y%m%dT%H%M%SZ); \
	run_dir=$(RAW_DIR)/$$run_id; \
	mkdir -p $$run_dir/mqtt $$run_dir/flows $$run_dir/honeypot; \
	touch $$run_dir/mqtt/mqtt.log $$run_dir/honeypot/cowrie.json; \
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
	if [ -z "$$(docker compose ps -q --status running capture)" ]; then \
	  echo "ERROR: the capture container is not running, so the pcap is incomplete."; exit 1; \
	fi; \
	docker compose stop $(EMULATORS) && \
	docker compose stop $(OTHER_SOURCES) && \
	docker compose stop capture && \
	docker compose down && \
	docker run --rm --network none -v "$$(pwd)/$(RAW_DIR)/$$run_id/flows:/out" \
	  --entrypoint python $(CAPTURE_IMAGE) flows.py && \
	rm -f $(CURRENT) && \
	echo "Testbed down. Raw logs in $(RAW_DIR)/$$run_id"

reset:
	docker compose down --volumes --remove-orphans
	rm -f $(CURRENT)
