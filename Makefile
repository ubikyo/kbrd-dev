TARGET := kbrd

REMOTE_DIR := /usr/lib/python3.14/site-packages/kbrd_dev
REMOTE_RESOURCES := /usr/share/kbrd

SERVICE := /etc/init.d/S70kbrd-dev

.PHONY: deploy restart

deploy:
	rsync -av --delete \
		--exclude='__pycache__/' \
		--exclude='*.pyc' \
		src/kbrd_dev/ \
		$(TARGET):$(REMOTE_DIR)/

	rsync -av --delete \
		resources/fonts/ \
		$(TARGET):$(REMOTE_RESOURCES)/fonts/

	rsync -av --delete \
		resources/media/ \
		$(TARGET):$(REMOTE_RESOURCES)/media/

	ssh $(TARGET) "$(SERVICE) restart"


restart:
	ssh $(TARGET) "$(SERVICE) restart"