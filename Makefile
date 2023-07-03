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
	yomi-skill \
		--game=yomi \
		--dest=site/index.html \
		--min-games=30 \
		--same-data \
		--model $(MODEL) \
		--validate \
		--warmup 500 \
		--samples 1000

matchups:
	yomi-skill \
		--game=yomi \
		--dest=site/index.html \
		--min-games=30 \
		--same-data \
		--model $(MODEL)

all-matchups: matchups

new-matchups:
	yomi-skill \
		--game=yomi \
		--dest=site/index.html \
		--min-games=30 \
		--new-data \
		--model $(MODEL) \
		--static-root=.

all-new-matchups: new-matchups
