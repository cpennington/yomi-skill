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
		--warmup=500 \
		--samples=1000

matchups:
	yomi-skill render \
		--dest='src-js/data/yomi' \
		--warmup=500 \
		--samples=1000

all-matchups: matchups

new-matchups:
	yomi-skill render \
		--dest='src-js/data/yomi' \
		--warmup 500 \
		--samples 1000

all-new-matchups: new-matchups

yomi2-matchups:
	yomi-skill yomi2 render --warmup 500 --samples 5000