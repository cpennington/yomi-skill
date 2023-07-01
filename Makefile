.PHONY: build

build:
	docker build container -t jupyter

upgrade:
	docker run -it  \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=volume,src=pipcache,dst=/root/.cache/pip" \
		--entrypoint="/bin/bash" \
		jupyter \
		-c "pip install --upgrade pip pip-tools && pip-compile --resolver=backtracking /code/container/requirements.in"

lab: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=volume,src=pipcache,dst=/root/.cache/pip" \
		--publish="127.0.0.1:9999:9999" \
		--memory=3g \
		--memory-swap=3g \
		jupyter

shell: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--entrypoint /bin/bash jupyter

matchups: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--memory=3g \
		--memory-swap=3g \
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=yomi \
		--dest=site/index.html \
		--min-games=30 \
		--same-data \
		--static-root=.

all-matchups: matchups

new-matchups: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--memory=3g \
		--memory-swap=3g \
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=yomi \
		--dest=site/index.html \
		--min-games=30 \
		--new-data \
		--static-root=.

all-new-matchups: new-matchups
