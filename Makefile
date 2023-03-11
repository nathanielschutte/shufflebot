
LOG_DIR=/var/log/shuffle
PROJECT_NAME=shuffle

.PHONY: all build run run-dev deploy test

.env:
	cp .env.example .env
	@sed -i 's/DISCORD_BOT_TOKEN=/DISCORD_BOT_TOKEN=$(DISCORD_BOT_TOKEN)/g' .env

test:
	mypy shuffle

build: .env
	docker build -t $(PROJECT_NAME):latest --target shuffle --file docker/Dockerfile .

run: build
	docker run -d --rm \
		-v $(LOG_DIR):/var/log/shuffle \
		--name "$(PROJECT_NAME)-run"
		$(PROJECT_NAME):latest

run-dev:
	@echo "mounting on $(PWD)"
	docker run -it --rm \
		-v $(PWD)/log/shuffle:/var/log/shuffle \
		-v $(LOG) $(PWD)/shuffle:/app/shuffle \
		-v $(PWD)/files:/var/lib/shuffle/files \
		$(PROJECT_NAME):latest /bin/bash

deploy:
	bash .deploy/deploy.sh
