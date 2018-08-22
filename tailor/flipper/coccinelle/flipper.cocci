//
// Add flipper bit fields to the Linux kernel
//
// Usage: spatch --sp-file this.cocci target.c --out-place -D macro=SET_FLIPPER_BIT
//        spatch -D macro=SET_FLIPPER_BIT -D ignoreInitFunctions -D blacklist="\/Documentation\/|\/tools\/|\/scripts\/|\/usr\/|\/boot\/|\/asm\/|\/firmware\/|\/flipper\.[ch]|\/include\/linux\/license\.h|\/arch\/x86\/vdso\/|\/drivers\/net\/wireless\/atmel.c|\/drivers\/gpu\/drm\/radeon\/mkregtable.c|\/lib\/gen_crc32table.c|\/lib\/crc32defs.h|\/lib\/raid6\/mktables.c" --no-show-diff --no-loops --use-cache -cache-prefix /tmp/occi/ --include-headers --sp-file this.cocci --dir linux --out-place
// Copyright: 2014 - FAU/Inf-LS4
// License: Licensed under GPL. See LICENSE or http://www.gnu.org/licenses/
// Author: Bernhard Heinloth <bernhard@heinloth.net>
// URL: http://vamos.informatik.uni-erlangen.de/


/* Known limitations:
	1. no patching of empty functions ( int x(){} )
	   Idea: Not a real problem?
	2. no patching of files without any include directive
	   Idea: at start of each function - ugly but valid.
	3. Patching macro functions will fail
	   Idea: add them to blacklist and wait for better spatch
*/

virtual ignoreInitFunctions


// Redirect output of map data to seperate file
@ initialize:python @
 m << virtual.mapfile;
@@
import sys
sys.stdout = open(m, "w")



// Initialize the blacklist, compiles the blacklist regex
// (if enabled by the spatch flag "-D blacklist=[Blacklist-RegEx]")
@ script:python initBlacklist @
b << virtual.blacklist;
@@
global blacklistLastFileCache;
global blacklistRegex;
blacklistLastFileCache=""
import re
blacklistRegex=re.compile(b)


// Get a(ny) position
// in order to retrieve the file name for blacklist processing
@ currentFile
  depends on initBlacklist @
metavariable a;
position p;
@@

a@p


// compare current file to blacklist regex
// (and continue with next file on match) including a simple cache mechanism.
@ script:python checkBlacklist
  depends on currentFile @
p << currentFile.p;
@@

global blacklistLastFileCache
global blacklistRegex;
if blacklistLastFileCache != p[0].file:
	if blacklistRegex.match(p[0].file):
		cocci.exit()
	else:
		blacklistLastFileCache = p[0].file


// Retrieve module_init (and module_exit) functions
// to avoid automatic bit sets on boot.
@ collectInitFunctions
  depends on ignoreInitFunctions @
identifier f;
declarer name module_init,
              module_exit;
@@

(
module_init(f);
|
module_exit(f);
)


// if there are some global include directives, append the flipper one
@ globalHeader
  depends on checkBlacklist @
@@

#include <...>
+#include <linux/flipper.h>


// if there are only some local include directives (without global ones),
// append the flipper include in the line above
@ localHeader
  depends on checkBlacklist && !globalHeader @
@@
+#include <linux/flipper.h>
#include "..."


// insert flipper macro in every non-empty function
// with an increasing counter index
@ replace @
identifier f,
           virtual.macro;
fresh identifier n = ""; // pure magic
declaration d;
statement s,t;
position p;
@@

f(...) {
(
(
... when != t
	when any
d@p
+;macro(n);
s
...
)
|
(
... when != t
	when any
d@p
+;macro(n);
)
|
(
+;macro(n);
s@p
...
)
)
}


// print the index, file and line number of each insertion
// (the index is necessary since there's an internal re-sort)
@ script:python print
  depends on replace @
p << replace.p;
n << replace.n;
@@

print "%013d\t%s:%s" % (float(n), p[0].file, p[0].line)


// remove the (fresh inserted) flipper macros from each init function
// (if enabled by the spatch flag "-D ignoreInitFunctions")
// Remember: The output will still reference to this function although it (and
//           its index bit) will never occur!
@ cleanInitFunctions
  depends on collectInitFunctions && replace @
identifier collectInitFunctions.f,
           virtual.macro;
@@

f(...){
...
-;macro(...);
...
}


// if there is no include (e.g. no other include directives) insert flipper
@ funcHeader
  depends on replace && !globalHeader && !localHeader @
identifier replace.f;
@@

+
+#include <linux/flipper.h>
f(...){
...
}

