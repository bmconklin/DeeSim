.PHONY: up down logs shell new clean

# Helper to extract arguments
ARGS = $(filter-out $@,$(MAKECMDGOALS))

# Start the application in detached mode
up:
	@if [ -n "$(CAMPAIGN)" ]; then \
		DM_ACTIVE_CAMPAIGN=$(CAMPAIGN) docker compose up -d --build; \
	elif [ -n "$(ARGS)" ]; then \
		DM_ACTIVE_CAMPAIGN=$(firstword $(ARGS)) docker compose up -d --build; \
	else \
		docker compose up -d --build; \
	fi

# Play in Terminal
play:
	@if [ -n "$(CAMPAIGN)" ]; then \
		DM_ACTIVE_CAMPAIGN=$(CAMPAIGN) docker compose run --rm -it app python src/play.py; \
	elif [ -n "$(ARGS)" ]; then \
		DM_ACTIVE_CAMPAIGN=$(firstword $(ARGS)) docker compose run --rm -it app python src/play.py; \
	else \
		docker compose run --rm -it app python src/play.py; \
	fi

# List of commands that accept arguments
SUPPORTED_COMMANDS := up play
SUPPORTS_ARGS := $(filter $(firstword $(MAKECMDGOALS)), $(SUPPORTED_COMMANDS))

%:
	@if [ -z "$(SUPPORTS_ARGS)" ]; then \
		echo "make: *** No rule to make target '$@'. Available commands: up, down, play, logs, shell, new, clean"; \
		exit 1; \
	fi

# Stop the application
down:
	docker compose down

# Follow logs
logs:
	docker compose logs -f

# Open a shell inside the container
shell:
	docker compose exec -it app /bin/bash

# Create a new campaign (interactive)
new:
	docker compose run --rm -it app python src/wizard.py

# Clean up docker artifacts
clean:
	docker compose down -v --rmi all
