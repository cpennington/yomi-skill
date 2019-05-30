
build:
	docker build container -t jupyter

lab: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=volume,src=pipcache,dst=/root/.cache/pip" \
		--mount="type=bind,src=$(PWD)/../bacon-replays,dst=/bacon-replays" \
		--publish="127.0.0.1:9999:9999" \
		--memory=4g \
		--memory-swap=4g \
		jupyter

shell: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--entrypoint /bin/bash jupyter

matchups: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--memory=4g \
		--memory-swap=4g \
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=yomi \
		--dest=site/index.html \
		--min-games=0 \
		--same-data \
		--static-root=.

bacon-matchups: build
	docker run -it  \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=bind,src=$(PWD)/../bacon-replays,dst=/bacon-replays" \
		--memory=4g \
		--memory-swap=4g \
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=bacon \
		--dest=site/bacon/index.html \
		--min-games=30 \
		--same-data \
		--static-root=..

bacon-vmatchups: build
	docker run -it  \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=bind,src=$(PWD)/../bacon-replays,dst=/bacon-replays" \
		--entrypoint /code/render_matchup_comparator.py \
		--memory=4g \
		--memory-swap=4g \
		jupyter \
		--game=bacon \
		--dest=site/bacon/versions/index.html \
		--min-games=30 \
		--same-data \
		--with-versions \
		--static-root=../..

all-matchups: matchups bacon-matchups bacon-vmatchups

new-matchups: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--memory=4g \
		--memory-swap=4g \
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=yomi \
		--dest=site/index.html \
		--min-games=0 \
		--new-data \
		--static-root=.

new-bacon-matchups: build
	docker run -it  \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=bind,src=$(PWD)/../bacon-replays,dst=/bacon-replays" \
		--memory=4g \
		--memory-swap=4g \
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=bacon \
		--dest=site/bacon/index.html \
		--min-games=30 \
		--new-data \
		--static-root=..

new-bacon-vmatchups: build
	docker run -it  \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=bind,src=$(PWD)/../bacon-replays,dst=/bacon-replays" \
		--entrypoint /code/render_matchup_comparator.py \
		--memory=4g \
		--memory-swap=4g \
		jupyter \
		--game=bacon \
		--dest=site/bacon/versions/index.html \
		--min-games=30 \
		--new-data \
		--with-versions \
		--static-root=../..

all-new-matchups: new-matchups new-bacon-matchups new-bacon-vmatchups
