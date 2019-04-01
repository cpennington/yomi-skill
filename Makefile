
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
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=yomi \
		--dest=index.html \
		--min-games=0 \
		--same-data

bacon-matchups: build
	docker run -it  \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=bind,src=$(PWD)/../bacon-replays,dst=/bacon-replays" \
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=bacon \
		--dest=bacon.html \
		--min-games=30 \
		--same-data

bacon-vmatchups: build
	docker run -it  \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=bind,src=$(PWD)/../bacon-replays,dst=/bacon-replays" \
		--entrypoint /code/render_matchup_comparator.py \
		jupyter \
		--game=bacon \
		--dest=bacon-versions.html \
		--min-games=30 \
		--same-data \
		--with-versions
