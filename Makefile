
PROJECT_NAME=shuffle

.env:
	cp .env.example .env
	sed 's/DISCORD_BOT_TOKEN=/DISCORD_BOT_TOKEN=$(DISCORD_BOT_TOKEN)/g' .env > .env

build: .env
	docker build -t $(PROJECT_NAME):latest --target shuffle --file docker/Dockerfile .

run: build
	docker run -it --rm $(PROJECT_NAME):latest
