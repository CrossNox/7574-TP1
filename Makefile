SHELL := /bin/bash
PWD := $(shell pwd)

GIT_REMOTE = github.com/CrossNox/7574-TP1
DOCKER_BIN=docker
DOCKER_COMPOSE_BIN=docker-compose

default: docker-image

docker-image:
	$(DOCKER_BIN) build -f ./docker/server-Dockerfile -t "7574-server:latest" .
	$(DOCKER_BIN) build -f ./docker/client-Dockerfile -t "7574-client:latest" .
.PHONY: docker-image

docker-compose-scenario1: docker-image
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario1.yaml up -d --build
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario1.yaml logs -f
.PHONY: docker-compose-scenario1

docker-compose-scenario1-down:
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario1.yaml stop -t 1
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario1.yaml down --volumes

.PHONY: docker-compose-scenario1-down

docker-compose-scenario2: docker-image
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario2.yaml up -d --build
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario2.yaml logs -f
.PHONY: docker-compose-scenario2

docker-compose-scenario2-down:
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario2.yaml stop -t 1
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario2.yaml down --volumes
.PHONY: docker-compose-scenario2-down

docker-compose-scenario3: docker-image
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario3.yaml up -d --build
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario3.yaml logs -f
.PHONY: docker-compose-scenario3

docker-compose-scenario3-down:
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario3.yaml stop -t 1
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario3.yaml down --volumes
.PHONY: docker-compose-scenario3-down

docker-compose-scenario4: docker-image
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario4.yaml up -d --build
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario4.yaml logs -f
.PHONY: docker-compose-scenario4

docker-compose-scenario4-down:
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario4.yaml stop -t 1
	$(DOCKER_COMPOSE_BIN) -f ./docker/docker-compose-scenario4.yaml down --volumes
.PHONY: docker-compose-scenario4-down
