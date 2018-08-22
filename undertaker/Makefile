# Add .d to Make's recognized suffixes.
SUFFIXES += .d

#We don't need to clean up when we're making these targets
NODEPS:=clean clean-check

CFLAGS = -Wall -Wextra -O2
CPPFLAGS = -I../scripts/kconfig -I../picosat
CXXFLAGS = $(CFLAGS) -std=gnu++11

# use g++ for linking, will automaticly use "-lstdc++ -lm" libraries
CC = g++

LDFLAGS =
BOOST_LIBS = -lboost_system -lboost_regex -lboost_filesystem -lboost_thread -lboost_chrono
LDLIBS = $(BOOST_LIBS) -lpthread

# LDCOV = -coverage
ifdef LDCOV
	LDLIBS += $(LDCOV)
endif

# DEBUG = -g3 -DDEBUG
# to compile with debug, compile like this:
# make DEBUG="-g3 -DDEBUG"
ifdef DEBUG
	CFLAGS += $(DEBUG)
endif

###################################################################################################
# static linking
# for this option to work, there have to be static versions of the boost libraries on your system!
# On Ubuntu, that's the default case when you install the boost libraries.
# ("locate libboost_filesystem.a" might help to ensure they are there)
ifdef STATIC
	LDFLAGS += -static
endif

###################################################################################################
# local Puma

ifneq ($(LOCALPUMA),)
CXXFLAGS += -Wno-unused-local-typedefs -Wno-unused-parameter
CPPFLAGS += -I$(LOCALPUMA)/include -I$(LOCALPUMA)/extern
PUMALIB = $(LOCALPUMA)/lib/linux-release/libPuma.a
else
LDLIBS += -lPuma
endif

###################################################################################################

PARSEROBJ = KconfigWhitelist.o Logging.o Tools.o \
		BoolExpLexer.o BoolExpParser.o BoolExpSymbolSet.o BoolExpSimplifier.o \
		BoolExpGC.o bool.o CNFBuilder.o PicosatCNF.o \
		ConditionalBlock.o PumaConditionalBlock.o RsfReader.o ModelContainer.o \
		ConfigurationModel.o RsfConfigurationModel.o CnfConfigurationModel.o \
		BlockDefectAnalyzer.o CoverageAnalyzer.o SatChecker.o

SATYROBJ = KconfigWhitelist.o Logging.o Tools.o \
		BoolExpLexer.o BoolExpParser.o BoolExpSymbolSet.o BoolExpSimplifier.o \
		BoolExpGC.o bool.o CNFBuilder.o PicosatCNF.o \
		ExpressionTranslator.o SymbolTranslator.o SymbolTools.o SymbolParser.o \
		KconfigAssumptionMap.o

PROGS = undertaker predator rsf2cnf satyr
TESTPROGS = test-SatChecker test-ConditionalBlock test-ConfigurationModel \
            test-Bool test-CNFBuilder test-BoolExpSymbolSet test-PicosatCNF

DEPFILES:=$(patsubst %.o,%.d,$(PARSEROBJ) $(SATYROBJ)) undertaker.d satyr.d


all: $(PROGS)

undertaker: libparser.a ../picosat/libpicosat.a $(PUMALIB)
rsf2cnf: libparser.a ../picosat/libpicosat.a
predator: predator.o PredatorVisitor.o $(PUMALIB)
satyr: libsatyr.a zconf.tab.o ../picosat/libpicosat.a

ifneq ($(LOCALPUMA),)
$(PUMALIB):
	$(MAKE) -C $(LOCALPUMA) compile
endif

../picosat/libpicosat.a:
	$(MAKE) -C .. picosat/libpicosat.a

../version.h:
	$(MAKE) -C .. version.h

undertaker.d rsf2cnf.d satyr.d: ../version.h


BoolExpLexer.cpp: BoolExpParser.cpp BoolExpLexer.l
	flex -o$@ BoolExpLexer.l

BoolExpParser.cpp: BoolExpParser.y
	bison -o $@ --defines=BoolExpParser.h $<

stack.hh location.hh postion.hh: BoolExpParser.cpp

BoolExpLexer.d: BoolExpLexer.cpp BoolExpParser.h location.hh stack.hh
BoolExpParser.d: BoolExpParser.cpp


location.hh: position.hh

bool.o: bool.cpp bool.h BoolExpParser.o

libparser.a: $(DEPFILES) $(PARSEROBJ)
	ar r $@ $(PARSEROBJ)

libsatyr.a: $(DEPFILES) $(SATYROBJ)
	ar r $@ $(SATYROBJ)

zconf.tab.o: ../scripts/kconfig/zconf.tab.o
	ln -sf $< $@

../scripts/kconfig/zconf.tab.o:
	$(MAKE) -C .. scripts/kconfig/dumpconf

#Don't create dependencies when we're cleaning, for instance
ifeq (0, $(words $(filter $(MAKECMDGOALS), $(NODEPS))))
    #Chances are, these files don't exist.  GMake will create them and
    #clean up automatically afterwards
    -include $(DEPFILES)
endif

#This is the rule for creating the dependency files
%.d: %.cpp
	 @$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MM -MG $< > $@

test-%: test-%.cpp libparser.a ../picosat/libpicosat.a $(PUMALIB)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -g -O0 -o $@ $^ -lcheck -lrt -lsubunit $(LDFLAGS) $(LDLIBS)

clean: clean-check
	rm -rf *.o *.a *.gcda *.gcno *.d
	rm -rf coverage-wl.cnf
	rm -rf $(PROGS) $(TESTPROGS)
	rm -rf location.hh stack.hh position.hh BoolExpParser.hh
	rm -rf BoolExpParser.cpp BoolExpLexer.cpp

###################################################################################################
# check targets

CHECK_TARGETS = check-undertaker check-libs check-rsf2cnf check-coverage check-satyr

clean-check:
	find coverage-tests validation/ \
	                 \( -name "*.c.output.expected" \
	                 -o -name "*.c.output.got" \
	                 -o -name "*.c.output.diff" \
	                 -o -name "*.c.error.expected" \
	                 -o -name "*.c.error.got" \
	                 -o -name "*.c.error.diff" \
	                 -o -name "*.c.config*" \
	                 -o -name "*.c.cppflags*" \
	                 -o -name "*.c.source*" \
	                 -o -name "*.dead" \
	                 -o -name "*.dead.mus" \
	                 -o -name "*.undead" \
	                 \) -delete
	rm -vf coverage-tests/coverage-cat.c.got
	@$(MAKE) -C validation-rsf2cnf clean

check-libs: $(TESTPROGS)
	@for t in $^; do echo "Executing test $$t"; ./$$t || exit 1; done

check-rsf2cnf: rsf2cnf
	./rsf2cnf \
	    -m validation/coverage-wl.model \
	    -r validation/coverage-wl.rsf \
	    -W validation/coverage-wl.whitelist \
	    -B validation/coverage-wl.blacklist > coverage-wl.cnf
	@if ! diff -q coverage-wl.cnf validation/coverage-wl.cnf-ref; then \
	    diff -u validation/coverage-wl.cnf-ref coverage-wl.cnf; false; fi
	@$(MAKE) -C validation-rsf2cnf check

# coverage analysis will create validation/sched.c.config*
check-coverage: undertaker predator
	./undertaker -j coverage -C simple_decision -m kconfig-dumps/models validation/sched.c
#	we expect between 5 and 30 solutions
	test `find validation -name 'sched.c.config*' | wc -l` -gt 5
	test `find validation -name 'sched.c.config*' | wc -l` -lt 30
	md5sum validation/sched.c.config* | awk '// {print $$1}' | sort | uniq -c \
		| awk '// { if ($$1 != 1) { print "duplicate solutions found" ; exit 1 } }' \
		|| md5sum validation/sched.c.config* | sort
	if grep -q '^CONFIG_IA64=y' validation/sched.c.config*; then echo "IA64 must not be enabled!"; false ; fi
	if grep -q '^CONFIG_CHOICE' validation/sched.c.config*; then echo "must not contain CONFIG_CHOICE*"; false ; fi
	cd coverage-tests && env PATH=$(CURDIR):$(PATH) ./run-tests

check-satyr: satyr
	@cd validation-satyr && ./checkall.sh

check-undertaker: undertaker
	cd def-tests && env PATH=$(CURDIR):$(PATH) ./run-tests
	cd validation && env PATH=$(CURDIR):$(CURDIR)/../picosat:$(PATH) ./test-suite -t $$(getconf _NPROCESSORS_ONLN)

check: $(PROGS)
	@$(MAKE) -s clean-check
	@$(MAKE) -C kconfig-dumps all
	@$(MAKE) real-check

real-check: $(CHECK_TARGETS)

###################################################################################################
# gcov is a tool to measure code coverage while running the programs. Here we build our tools with
# gcov and run make check, thus we measure the code coverage of our tests.

run-lcov:
	$(MAKE) -B DEBUG="-g -O0 -fprofile-arcs -ftest-coverage" LDCOV="-coverage -lgcov" all $(TESTPROGS)
	rm -rf coverage-html ; mkdir coverage-html
	lcov --directory $(CURDIR) --zerocounters
	-$(MAKE) check
	lcov --directory $(CURDIR) --capture --output-file coverage-html/undertaker.info.in
	lcov -e coverage-html/undertaker.info.in "$(CURDIR)*" --output-file coverage-html/undertaker.info
	genhtml -o coverage-html coverage-html/undertaker.info

###################################################################################################
# other targets

docs:
	doxygen

###################################################################################################

FORCE:
.PHONY: all clean clean-% FORCE check check-% real-check run-lcov docs
