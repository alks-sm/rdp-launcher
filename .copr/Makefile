# Сборка SRPM прямо из git для COPR (copr-cli buildscm --method make_srpm).
# COPR запускает `make srpm` в корне репозитория и ожидает SRPM в $(outdir).

NAME    := rdp-launcher
VERSION := $(shell sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)

srpm:
	@mkdir -p $(outdir)
	tar --transform 's,^\.,$(NAME)-$(VERSION),' \
	    --exclude=.git --exclude=__pycache__ --exclude='*.pyc' --exclude=build \
	    -czf $(outdir)/$(NAME)-$(VERSION).tar.gz .
	rpmbuild -bs packaging/$(NAME).spec \
	    --define "_sourcedir $(outdir)" \
	    --define "_srcrpmdir $(outdir)" \
	    --define "_builddir $(outdir)"
	@echo "SRPM: $(outdir)/$(NAME)-$(VERSION)-1.src.rpm"
