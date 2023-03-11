
LOG_DIR=/var/log/shuffle
PROJECT_NAME=shuffle

.PHONY: all build run run-dev deploy

.env:
	cp .env.example .env
	sed 's/DISCORD_BOT_TOKEN=/DISCORD_BOT_TOKEN=$(DISCORD_BOT_TOKEN)/g' .env > .env

build: .env
	docker build -t $(PROJECT_NAME):latest --target shuffle --file docker/Dockerfile .

run: build
	docker run -d -v $(LOG_DIR):/var/log/shuffle --rm $(PROJECT_NAME):latest

run-dev: build
	docker run -it --rm \
		-v $(PWD)/log/shuffle:/var/log/shuffle \
		-v $(LOG) $(PWD)/shuffle:/app/shuffle \
		-v $(PWD)/files:/var/lib/shuffle/files \
		$(PROJECT_NAME):latest /bin/bash

deploy:
	bash .deploy/deploy.sh
