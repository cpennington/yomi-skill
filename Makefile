.PHONY: build

MODEL ?= char_skill_elo_skill_deficit

build:
	docker build container -t jupyter

upgrade:
	docker run -it  \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--entrypoint="/bin/bash" \
		jupyter \
		-c "pip install --upgrade pip pip-tools && python -m piptools compile -o /code/container/requirements.txt --resolver=backtracking /code/pyproject.toml"

lab:
	jupyter

validate:
	yomi-skill validate \
		--game=yomi \
		--same-data \
		--min-games=30 \
		--model=$(MODEL) \
		--warmup=500 \
		--samples=1000

matchups:
	yomi-skill render \
		--game=yomi \
		--dest=site/index.html \
		--same-data \
		--min-games=30 \
		--model=$(MODEL) \
		--warmup=500 \
		--samples=1000

all-matchups: matchups

new-matchups:
	yomi-skill render \
		--game=yomi \
		--dest=site/index.html \
		--new-data \
		--model $(MODEL) \
		--static-root=. \
		--warmup 500 \
		--samples 1000

all-new-matchups: new-matchups
