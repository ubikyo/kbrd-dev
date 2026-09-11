TARGET := kbrd

REMOTE_DIR := /usr/lib/python3.14/site-packages/kbrd_dev
REMOTE_RESOURCES := /usr/share/kbrd

SERVICE := /etc/init.d/S70kbrd-dev

.PHONY: deploy restart

deploy:
	@printf "\033[47;30m %-60s \033[0m\n" " KBRD-DEV : déploiement Python "
	rsync -av --delete \
		--exclude='__pycache__/' \
		--exclude='*.pyc' \
		src/kbrd_dev/ \
		$(TARGET):$(REMOTE_DIR)/

	@printf "\033[47;30m %-60s \033[0m\n" " KBRD-DEV : redémarrage du service "
	ssh $(TARGET) "$(SERVICE) restart"

	@printf "\033[47;30m %-60s \033[0m\n" " KBRD-DEV : déploiement terminé "

restart:
	@printf "\033[47;30m %-60s \033[0m\n" " KBRD-DEV : redémarrage du service "
	ssh $(TARGET) "$(SERVICE) restart"