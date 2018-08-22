SATYR=$(CURDIR)/../undertaker/satyr
CONF=$(CURDIR)/../scripts/kconfig/conf
MODELS=$(wildcard *.fm)
CNFs=$(MODELS:.fm=.cnf)
ALLYESCONFIGS=$(MODELS:.fm=.allyesconfig)
ALLMODCONFIGS=$(MODELS:.fm=.allmodconfig)
ALLNOCONFIGS=$(MODELS:.fm=.allnoconfig)
ALLDEFCONFIGS=$(MODELS:.fm=.alldefconfig)
ALLCONFIGS=$(ALLYESCONFIGS) $(ALLNOCONFIGS) $(ALLMODCONFIGS) $(ALLDEFCONFIGS)

PREFIX=env KCONFIG_CONFIG=$@ ARCH="" KERNELVERSION=""

all: check

$(SATYR):
	$(MAKE) -s -C $(@D) $(@F)

$(CONF):
	$(MAKE) -s -C .. $(@F)

%.cnf: %.fm
	$(SATYR) $< -c $@

%.allyesconfig: %.fm $(CONF) $(SATYR)
	$(PREFIX) $(CONF) $< --allyesconfig > /dev/null || (echo "Calculation of $@ failed" && exit 1)
	$(SATYR) $< -a $@ 2> /dev/null || (echo "call of satyr on $@ failed" && exit 1)

%.allnoconfig: %.fm $(CONF) $(SATYR)
	$(PREFIX) $(CONF) $< --allnoconfig > /dev/null || (echo "Calculation of $@ failed" && exit 1)
	$(SATYR) $< -a $@ 2> /dev/null || (echo "call of satyr on $@ failed" && exit 1)

%.allmodconfig: %.fm $(CONF) $(SATYR)
	$(PREFIX) $(CONF) $< --allmodconfig > /dev/null || (echo "Calculation of $@ failed" && exit 1)
	$(SATYR) $< -a $@ 2> /dev/null || (echo "call of satyr on $@ failed" && exit 1)

%.alldefconfig: %.fm $(CONF) $(SATYR)
	$(PREFIX) $(CONF) $< --alldefconfig > /dev/null || (echo "Calculation of $@ failed" && exit 1)
	$(SATYR) $< -a $@ 2> /dev/null || (echo "call of satyr on $@ failed" && exit 1)

check: $(ALLCONFIGS)

clean:
	rm -rf $(CNFs) $(ALLCONFIGS) *.*.old


.PHONY: check clean all
