.PHONY: up down test seed clean help demo

help:
	@echo "Hilly-Region Flash Flood & Landslide EWS (SIH 2026, PS 26192)"
	@echo ""
	@echo "Available commands:"
	@echo "  make demo   - Run the full live disaster replay & Kill-Internet resilience demo"
	@echo "  make up     - Build and launch Docker Compose services (PostGIS, Redis, Backend, Frontend)"
	@echo "  make down   - Stop all running Docker Compose services"
	@echo "  make test   - Run full unit and integration test suite via pytest"
	@echo "  make seed   - Seed database with 25 synthetic Uttarkashi pilot villages"
	@echo "  make clean  - Stop services and remove Docker volumes"

demo:
	@echo "=== [1/2] Running Online EWS Disaster Replay (Lead Time Advantage) ==="
	python scripts/replay_demo.py --scenario bhatwari_debris_flow_synthetic --speed 0
	@echo ""
	@echo "=== [2/2] Running 'Kill Internet' Autonomous Edge LoRa & Siren Fallback ==="
	python scripts/replay_demo.py --scenario bhatwari_debris_flow_synthetic --kill-internet --speed 0

up:
	docker compose up -d --build

down:
	docker compose down

test:
	python -m pytest tests/ -v

seed:
	python scripts/seed_data.py

clean:
	docker compose down -v
