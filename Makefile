
build:
	docker build container -t jupyter

lab: build
	docker run -it \
		--mount="type=bind,src=$(PWD),dst=/code" \
		--mount="type=volume,src=pipcache,dst=/root/.cache/pip" \
		--publish="127.0.0.1:8888:8888" \
		--memory=4g \
		--memory-swap=4g \
		jupyter

shell: build
	docker run -it  --mount="type=bind,src=$(PWD),dst=/src" --entrypoint /bin/bash jupyter
