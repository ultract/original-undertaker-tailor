OTHER_PROGS = tailor/undertaker-traceutil ziz/zizler
MANPAGES = doc/undertaker.1.gz doc/undertaker-linux-tree.1.gz doc/undertaker-kconfigdump.1.gz \
	doc/undertaker-kconfigpp.1.gz

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
SBINDIR ?= $(PREFIX)/sbin
LIBDIR ?= $(PREFIX)/lib
MANDIR ?= $(PREFIX)/share/man
DOCDIR ?= $(PREFIX)/share/doc
ETCDIR ?= $(PREFIX)/etc

VERSION=$(shell cat VERSION)

ifneq ($(LOCALPUMA),)
# to handle relative paths, call readlink
LOCALPUMA := $(shell readlink -e $(LOCALPUMA))
PUMALIB := $(LOCALPUMA)/lib/linux-release/libPuma.a
endif

ifneq (,$(DESTDIR))
SETUP_PY_EXTRA_ARG = --root=$(DESTDIR)
SETUP_PY_INSTALL_EXTRA_ARG = $(SETUP_PY_EXTRA_ARG)
endif

all: picosat/libpicosat.a checkpuma $(PUMALIB) FORCE
	$(MAKE) all_progs

all_progs: $(OTHER_PROGS) checkpuma undertaker_progs

undertaker_progs: checkpuma
	$(MAKE) -C undertaker/

version.h: generate-version.sh
	./$<

scripts/kconfig/conf: FORCE
	$(MAKE) -f Makefile.kbuild $(@F)

scripts/kconfig/dumpconf: scripts/kconfig/conf FORCE
	$(MAKE) -f Makefile.kbuild $(@F)

picosat/libpicosat.a:
	cd picosat && CFLAGS= ./configure -static -O
	$(MAKE) -C picosat

###################################################################################################
# Puma targets

localpuma: aspectc/Puma/
	LOCALPUMA=aspectc/Puma/ $(MAKE)

aspectc/Puma/: ac-woven-1.2.tar.gz
	tar -xf ac-woven-1.2.tar.gz
	mv aspectc++/ aspectc/

ac-woven-1.2.tar.gz:
	wget http://aspectc.org/releases/1.2/ac-woven-1.2.tar.gz

# exitcode 0 = successful compiled, exitcode 1 = error
PUMAINSTALLED := $(shell echo "int main(){}" | gcc -o /dev/null -x c - -lPuma 2>/dev/null ; echo $$?)

checkpuma:
ifeq ($(LOCALPUMA),)
ifeq (0, $(words $(filter $(MAKECMDGOALS), localpuma)))
ifneq (0, $(PUMAINSTALLED))
	$(error "No local Puma library found! Please call 'make localpuma' or specify a path to a copy of the pre-woven Puma sources via 'LOCALPUMA=/path/to/aspectc++/Puma/ make'")
endif
endif
endif

ifneq ($(LOCALPUMA),)
$(PUMALIB):
	CPPFLAGS="-Wno-unused-local-typedefs -Wno-unused-parameter" $(MAKE) -s -C $(LOCALPUMA) compile

clean-Puma:
	$(MAKE) -C $(LOCALPUMA) libclean
endif

###################################################################################################

undertaker/undertaker: FORCE checkpuma
	$(MAKE) -C undertaker undertaker

undertaker/predator: FORCE checkpuma
	$(MAKE) -C undertaker predator

undertaker/rsf2cnf: FORCE
	$(MAKE) -C undertaker rsf2cnf

tailor/undertaker-traceutil: FORCE
	$(MAKE) -C tailor undertaker-traceutil

undertaker/satyr: FORCE
	$(MAKE) -C undertaker satyr

ziz/zizler: FORCE
	$(MAKE) -C ziz zizler

conf: scripts/kconfig/conf

clean:
	$(MAKE) -C undertaker clean
	$(MAKE) -C ziz clean
	$(MAKE) -C python clean
	$(MAKE) -C tailor clean
	$(MAKE) -C fm clean
	rm -rf doc/*.gz
	@python2 setup.py clean

distclean: clean
	$(MAKE) -C undertaker clean-parsers
	$(MAKE) -f Makefile.kbuild clean
	test ! -f picosat/makefile || $(MAKE) -C picosat clean
	test ! -f $(LOCALPUMA)/Makefile || $(MAKE) clean-Puma

models: picosat/libpicosat.a
	$(MAKE) -C undertaker/kconfig-dumps/

###################################################################################################
# check targets

CHECK_TARGETS = check-undertaker check-ziz check-python check-tailor check-fm

check: all
	$(MAKE) real_check

real_check: $(CHECK_TARGETS)

check-undertaker:
	$(MAKE) -C undertaker check

check-ziz:
	$(MAKE) -C ziz check

check-python:
	$(MAKE) -C python check

check-tailor:
	$(MAKE) -C tailor check

check-fm:
	$(MAKE) -s -C fm check

###################################################################################################
# install and release

install: all $(MANPAGES)
	@install -d -v $(DESTDIR)$(BINDIR)
	@install -d -v $(DESTDIR)$(SBINDIR)
	@install -d -v $(DESTDIR)$(DOCDIR)
	@install -d -v $(DESTDIR)$(LIBDIR)/undertaker
	@install -d -v $(DESTDIR)$(ETCDIR)/undertaker
	@install -d -v $(DESTDIR)$(LIBDIR)/undertaker/tailor/ubuntu-boot
	@install -d -v $(DESTDIR)$(PREFIX)/share/emacs/site-lisp/undertaker
	@install -d -v $(DESTDIR)$(DOCDIR)/undertaker/tailor
	@install -d -v $(DESTDIR)$(MANDIR)/man1

	@install -v python/undertaker-calc-coverage $(DESTDIR)$(BINDIR)
	@install -v python/undertaker-kconfigdump $(DESTDIR)$(BINDIR)
	@install -v python/undertaker-checkpatch $(DESTDIR)$(BINDIR)
	@install -v python/vampyr-spatch-wrapper $(DESTDIR)$(BINDIR)
	@install -v python/fakecc $(DESTDIR)$(BINDIR)

	@install -v scripts/kconfig/dumpconf $(DESTDIR)$(LIBDIR)/undertaker

	@install -v tailor/undertaker-tailor $(DESTDIR)$(BINDIR)
	@install -v tailor/undertaker-tracecontrol-prepare-debian $(DESTDIR)$(BINDIR)
	@install -v tailor/undertaker-tracecontrol-prepare-ubuntu $(DESTDIR)$(BINDIR)
	@install -v tailor/undertaker-tracecontrol $(DESTDIR)$(BINDIR)
	@install -v tailor/undertaker-traceutil $(DESTDIR)$(SBINDIR)
	@cp -v tailor/lists/* $(DESTDIR)$(ETCDIR)/undertaker/
	@cp -v tailor/HOWTO $(DESTDIR)$(DOCDIR)/undertaker/tailor/
	@cp -v tailor/README $(DESTDIR)$(DOCDIR)/undertaker/tailor/
	@cp -r -v tailor/boot/* $(DESTDIR)$(LIBDIR)/undertaker/tailor/ubuntu-boot

	@install -v undertaker/predator $(DESTDIR)$(BINDIR)
	@install -v undertaker/undertaker $(DESTDIR)$(BINDIR)
	@install -v undertaker/undertaker-linux-tree $(DESTDIR)$(BINDIR)
	@install -v undertaker/undertaker-coreboot-tree $(DESTDIR)$(BINDIR)
	@install -v undertaker/undertaker-scan-head $(DESTDIR)$(BINDIR)
	@install -v undertaker/undertaker-busybox-tree $(DESTDIR)$(BINDIR)
	@install -v undertaker/rsf2cnf $(DESTDIR)$(BINDIR)
	@install -v undertaker/satyr $(DESTDIR)$(BINDIR)

	@install -v picosat/picomus $(DESTDIR)$(BINDIR)

	@install -v ziz/zizler $(DESTDIR)$(BINDIR)

	@install -v scripts/Makefile.list $(DESTDIR)$(LIBDIR)
	@install -v scripts/Makefile.list_recursion $(DESTDIR)$(LIBDIR)
	@install -v scripts/Makefile.list_fiasco $(DESTDIR)$(LIBDIR)

	@install -v -m 0644 contrib/undertaker.el $(DESTDIR)$(PREFIX)/share/emacs/site-lisp/undertaker

	@install -v -m 0644 -t $(DESTDIR)$(MANDIR)/man1 $(MANPAGES)

	@python2 setup.py build $(SETUP_PY_BUILD_EXTRA_ARG)
	@python2 setup.py install --prefix=$(PREFIX) $(SETUP_PY_INSTALL_EXTRA_ARG)

dist: clean
	tar -czvf ../undertaker-$(VERSION).tar.gz . \
		--show-transformed-names \
		--transform 's,^./,undertaker-$(VERSION)/,'\
		--exclude=*~ \
		--exclude=*.rsf \
		--exclude=*.model \
		--exclude-vcs \
		--exclude="*nfs*" \
		--exclude="*git*" \
		--exclude=*.tar.gz \
		--exclude="*.html"

###################################################################################################
# other targets

undertaker-lcov: FORCE checkpuma
	$(MAKE) -C undertaker run-lcov

docs:
	$(MAKE) -C undertaker docs

%.1.gz: %.1
	gzip < $< > $@

###################################################################################################

FORCE:
.PHONY: FORCE all all_progs check undertaker-lcov $(CHECK_TARGETS) docs regenerate_parsers \
	undertaker_progs localpuma clean-puma checkpuma
