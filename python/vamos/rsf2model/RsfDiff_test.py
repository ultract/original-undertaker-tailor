
""" Unit tests for RsfDiff """

# Copyright (C) 2015 Valentin Rothberg <valentinrothberg@gmail.com>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest2 as t
import StringIO

from vamos.rsf2model.RsfDiff import RsfDiff
from vamos.rsf2model.RsfReader import RsfReader

class TestDiff(t.TestCase):

    def setUp(self):
        pass


    def test_diff_prompts(self):
        """ Diff prompts.  If the number of prompts of feature 'A' differ, a
        list in the form [old value, new value] is stored in
        diff.changes["MOD_A"] in the sub-dictionary "ADD_PROMPT" or
        "REM_PROMPT". """

        rsf_a = \
"""
Item        64BIT   boolean
HasPrompts  64BIT   1
Item        FOO     boolean
HasPrompts  FOO     0
Item        BAR     boolean
HasPrompts  BAR     1
"""
        rsf_b = \
"""
Item        64BIT   boolean
HasPrompts  64BIT   0
Item        FOO     boolean
HasPrompts  FOO     1
Item        BAR     boolean
HasPrompts  BAR     2
"""

        reader_a = RsfReader(StringIO.StringIO(rsf_a))
        reader_b = RsfReader(StringIO.StringIO(rsf_b))

        diff = RsfDiff(reader_a, reader_b)
        diff.diff()

#-HasPrompts  64BIT   1
#+HasPrompts  64BIT   2
        self.assertIn("REM_PROMPT", diff.changes["MOD_64BIT"])
        self.assertEqual(['1', '0'], diff.changes["MOD_64BIT"]["REM_PROMPT"])

#-HasPrompts  FOO     0
#+HasPrompts  FOO     1
        self.assertIn("ADD_PROMPT", diff.changes["MOD_FOO"])
        self.assertEqual(['0', '1'], diff.changes["MOD_FOO"]["ADD_PROMPT"])

#-HasPrompts  BAR     1
#+HasPrompts  BAR     2
        self.assertIn("ADD_PROMPT", diff.changes["MOD_BAR"])
        self.assertEqual(['1', '2'], diff.changes["MOD_BAR"]["ADD_PROMPT"])


    def test_diff_types(self):
        """ Diff types.  If the type of feature 'A' changed, a list in the form
        of [old type, new type] is stored in diff.changes["MOD_A"] in the
        sub-dictionary "MOD_TYPE". """

        rsf_a = \
"""
Item        64BIT   tristate
HasPrompts  64BIT   1
Default     64BIT   "ARCH!=CVALUE_i386"     "y"
Definition  64BIT   "arch/x86/Kconfig:2"
"""
        rsf_b = \
"""
Item        64BIT   boolean
HasPrompts  64BIT   1
Default     64BIT   "ARCH!=CVALUE_i386"     "y"
Definition  64BIT   "arch/x86/Kconfig:2"
"""

        reader_a = RsfReader(StringIO.StringIO(rsf_a))
        reader_b = RsfReader(StringIO.StringIO(rsf_b))

        diff = RsfDiff(reader_a, reader_b)
        diff.diff()

#-Item        64BIT   tristate
#+Item        64BIT   boolean
        self.assertIn("MOD_TYPE", diff.changes["MOD_64BIT"])
        self.assertEqual(['tristate', 'boolean'], diff.changes["MOD_64BIT"]["MOD_TYPE"])


    def test_add_rem_features(self):
        """ Diff added and removed features.  If feature 'A' is added,
        diff.changes has a key "ADD_A".  If feature 'A' is removed,
        diff.changes has a key "REM_A". """

        rsf_a = \
"""
Item        64BIT   boolean
HasPrompts  64BIT   1
Default     64BIT   "ARCH!=CVALUE_i386"     "y"
Definition  64BIT   "arch/x86/Kconfig:2"
Item        FOO     tristate
Default     FOO     "ARCH!=CVALUE_i386"     "y"
Definition  FOO     "foo/Kconfig:1"
"""
        rsf_b = \
"""
Item        64BIT   boolean
HasPrompts  64BIT   1
Default     64BIT   "ARCH!=CVALUE_i386"     "y"
Definition  64BIT   "arch/x86/Kconfig:2"
Item        32BIT   boolean
Depends     32BIT   "POO"
Definition  32BIT   "arch/x86/Kconfig:2"
"""

        reader_a = RsfReader(StringIO.StringIO(rsf_a))
        reader_b = RsfReader(StringIO.StringIO(rsf_b))

        diff = RsfDiff(reader_a, reader_b)
        diff.diff()

#-Item        FOO     tristate
#-Default     FOO     "ARCH!=CVALUE_i386"     "y"
#-Definition  FOO     "foo/Kconfig:1"
        self.assertIn("REM_FOO", diff.changes)

#+Item        32BIT   boolean
#+Depends     32BIT   "POO"
#+Definition  32BIT   "arch/x86/Kconfig:2"
        self.assertIn("ADD_32BIT", diff.changes)

# Nothing changed for 64BIT
        self.assertNotIn("MOD_64BIT", diff.changes)


    def test_diff_depends(self):
        """ Diff depends.  Dependencies can be added ("ADD_DEPENDS"), removed
        ("REM_DEPENDS") and modified ("MOD_DEPENDS").  A modification to
        dependencies may be adding or removing new references which are
        accordingly stored as sorted lists in the sub-sub-dictionary
        diff.changes["MOD_A"]["MOD_DEPENDS"]["{ADD,REM}_REFERENCES"].  Another
        modification to dependencies may be changing the boolean condition (see
        below).  The condition is only checked when no references has been
        added or removed. """

        rsf_a = \
"""
Item        64BIT   tristate
Item        X86_64  boolean
Depends     X86_64  "64BIT"
Item        FOO     boolean
Depends     FOO     "X86 && BAR"
Item        PERF_EVENTS_INTEL_UNCORE    boolean
Depends     PERF_EVENTS_INTEL_UNCORE    "PERF_EVENTS && CPU_SUP_INTEL && PCI"
"""
        rsf_b = \
"""
Item        64BIT   boolean
Depends     64BIT   "NEW_DEPENDENCY"
Item        X86_64  boolean
Depends     X86_64  "!32BIT && HURZ"
Item        FOO     boolean
Depends     FOO     "X86 || BAR"
Item        PERF_EVENTS_INTEL_UNCORE    boolean
Default     PERF_EVENTS_INTEL_UNCORE    "y"     "PERF_EVENTS && CPU_SUP_INTEL && PCI"
"""

        reader_a = RsfReader(StringIO.StringIO(rsf_a))
        reader_b = RsfReader(StringIO.StringIO(rsf_b))

        diff = RsfDiff(reader_a, reader_b, True)
        diff.diff()

#-Depends     X86_64  "64BIT"
#+Depends     X86_64  "!32BIT && HURZ"
        self.assertIn("MOD_DEPENDS", diff.changes["MOD_X86_64"])
        self.assertEqual(["32BIT", "HURZ"], diff.changes["MOD_X86_64"]["MOD_DEPENDS"]["ADD_REFERENCES"])
        self.assertEqual(["64BIT"], diff.changes["MOD_X86_64"]["MOD_DEPENDS"]["REM_REFERENCES"])

#-Depends     FOO     "X86 && BAR"
#+Depends     FOO     "X86 || BAR"
        self.assertEqual(["X86 && BAR", "X86 || BAR"], diff.changes["MOD_FOO"]["MOD_DEPENDS"]["MOD_EXPRESSION"])

#+Depends     64BIT   "NEW_DEPENDENCY"
        self.assertIn("ADD_DEPENDS", diff.changes["MOD_64BIT"])
        self.assertEqual(["NEW_DEPENDENCY"], diff.changes["MOD_64BIT"]["ADD_DEPENDS"])

#-Depends     PERF_EVENTS_INTEL_UNCORE    "PERF_EVENTS && CPU_SUP_INTEL && PCI"
#+Default     PERF_EVENTS_INTEL_UNCORE    "y"     "PERF_EVENTS && CPU_SUP_INTEL && PCI"
        self.assertIn("REM_DEPENDS", diff.changes["MOD_PERF_EVENTS_INTEL_UNCORE"])
        self.assertEqual(["PERF_EVENTS && CPU_SUP_INTEL && PCI"], diff.changes["MOD_PERF_EVENTS_INTEL_UNCORE"]["REM_DEPENDS"])


    def test_diff_selects(self):
        """ Diff selects.  Select targets can be added ("ADD_SELECTS"), removed
        ("REM_SELECTS") and modified ("MOD_SELECTS").  A modification to
        selects may be adding or removing new references which are
        accordingly stored as sorted lists in the sub-sub-dictionary
        diff.changes["MOD_A"]["MOD_DSELECTS"]["{ADD,REM}_REFERENCES_$TARGET"].
        Another modification to selects may be changing the boolean expression
        (see below).  The expression is only checked when no references has been
        added or removed. """

        rsf_a = \
"""
Item        FOO boolean
Depends     FOO "X86 || BAR"
ItemSelects FOO "AAA" "BBB || CCC || DDD"
ItemSelects FOO "BAR"   "FOO_BAR"
ItemSelects FOO "HAAA"
Definition  FOO "foo/Kconfig:1"
"""
        rsf_b = \
"""
Item        FOO boolean
Depends     FOO "X86 || BAR"
ItemSelects FOO "AAA" "CCC && BBB && DDD"
ItemSelects FOO "BAR"   "FOO_BAR_2 || BAR_2"
ItemSelects FOO "TEST"  "y"
Definition  FOO "foo/Kconfig:1"
"""
        reader_a = RsfReader(StringIO.StringIO(rsf_a))
        reader_b = RsfReader(StringIO.StringIO(rsf_b))

        diff = RsfDiff(reader_a, reader_b, True)
        diff.diff()

#+ItemSelects FOO "TEST"  "y"
        self.assertIn("ADD_SELECTS", diff.changes["MOD_FOO"])
        self.assertEqual(["TEST"], diff.changes["MOD_FOO"]["ADD_SELECTS"])

#-ItemSelects FOO "HAAA"
        self.assertIn("REM_SELECTS", diff.changes["MOD_FOO"])
        self.assertEqual(["HAAA"], diff.changes["MOD_FOO"]["REM_SELECTS"])

#-ItemSelects FOO "BAR"   "FOO_BAR"
#+ItemSelects FOO "BAR"   "FOO_BAR_2 || BAR_2"
        self.assertIn("MOD_SELECTS", diff.changes["MOD_FOO"])
        self.assertEqual(["FOO_BAR"], diff.changes["MOD_FOO"]["MOD_SELECTS"]["REM_REFERENCES_BAR"])
        self.assertEqual(["BAR_2", "FOO_BAR_2"], diff.changes["MOD_FOO"]["MOD_SELECTS"]["ADD_REFERENCES_BAR"])

#-ItemSelects FOO "AAA" "CCC || BBB || DDD"
#+ItemSelects FOO "AAA" "CCC && BBB && DDD"
        self.assertEqual(["(BBB || CCC || DDD)", "(CCC && BBB && DDD)"], diff.changes["MOD_FOO"]["MOD_SELECTS"]["MOD_CONDITION_AAA"])


    def test_diff_defaults(self):
        """ Diff defaults.  Default values can be added ("ADD_DEFAULTS"), removed
        ("REM_DEFAULTS") and modified ("MOD_DEFAULTS").  A modification to
        defaults may be adding or removing new references which are
        accordingly stored as sorted lists in the sub-sub-dictionary
        diff.changes["MOD_A"]["MOD_DEFAULTS"]["{ADD,REM}_REFERENCES_$VALUE"].
        Another modification to selects may be changing the boolean condition
        (see below).  The condition is only checked when no references has been
        added or removed. """

        rsf_a = \
"""
Item        FOO boolean
Default     FOO "y" "BAR"
Default     FOO "AAA" "BBB || CCC"
Default     FOO "BBB" "EEE || FFF"
Default     FOO "n" "BAR = n"
Definition  FOO "foo/Kconfig:1"
"""
        rsf_b = \
"""
Item        FOO boolean
Default     FOO "y" "BAR"
Default     FOO "y" "HURZ"
Default     FOO "AAA" "BBB && CCC"
Default     FOO "BBB" "EEE"
Default     FOO "BAR" "y"
Default     FOO "BAR2" "y"
Default     FOO "FOO || BAR" ""
Definition  FOO "foo/Kconfig:1"
"""
        reader_a = RsfReader(StringIO.StringIO(rsf_a))
        reader_b = RsfReader(StringIO.StringIO(rsf_b))

        diff = RsfDiff(reader_a, reader_b, True)
        diff.diff()

#+Default     FOO "BAR" "y"
#+Default     FOO "BAR2" "y"
#+Default     FOO "FOO || BAR" "y"
        self.assertIn("ADD_DEFAULTS", diff.changes["MOD_FOO"])
        self.assertEqual(["BAR", "BAR2", "FOO || BAR"], diff.changes["MOD_FOO"]["ADD_DEFAULTS"])

#-Default     FOO "n" "BAR = n"
        self.assertIn("REM_DEFAULTS", diff.changes["MOD_FOO"])
        self.assertEqual(["n"], diff.changes["MOD_FOO"]["REM_DEFAULTS"])

#+Default     FOO "y" "HURZ"
        self.assertIn("MOD_DEFAULTS", diff.changes["MOD_FOO"])
        self.assertEqual(["HURZ"], diff.changes["MOD_FOO"]["MOD_DEFAULTS"]["ADD_REFERENCES_y"])

#-Default     FOO "BBB" "EEE || FFF"
#+Default     FOO "BBB" "EEE"
        self.assertIn("MOD_DEFAULTS", diff.changes["MOD_FOO"])
        self.assertEqual(["FFF"], diff.changes["MOD_FOO"]["MOD_DEFAULTS"]["REM_REFERENCES_BBB"])

#-Default     FOO "AAA" "BBB || CCC"
#+Default     FOO "AAA" "BBB && CCC"
        self.assertEqual(["(BBB || CCC)", "(BBB && CCC)"], diff.changes["MOD_FOO"]["MOD_DEFAULTS"]["MOD_CONDITION_AAA"])


    def test_getters(self):
        """ Test the diff.get_* methods. """

        rsf_a = \
"""
Item    FOO_2       boolean
Item    FOO_1       boolean
Item    MOD_ME_1    boolean
Depends MOD_ME_1    "BAR"
"""
        rsf_b = \
"""
Item    BAR_2       tristate
Item    ABC_1       tristate
Item    MOD_ME_1    boolean
Depends MOD_ME_1    "BAR || FOO"
"""

        reader_a = RsfReader(StringIO.StringIO(rsf_a))
        reader_b = RsfReader(StringIO.StringIO(rsf_b))

        diff = RsfDiff(reader_a, reader_b, True)
        diff.diff()

#+Item    BAR_2       tristate
#+Item    ABC_1       tristate
        self.assertEqual(["ABC_1", "BAR_2"], diff.get_added_features())

#-Item    FOO_2       boolean
#-Item    FOO_1       boolean
        self.assertEqual(["FOO_1", "FOO_2"], diff.get_removed_features())

#-Depends MOD_ME_1    "BAR"
#+Depends MOD_ME_1    "BAR || FOO"
        self.assertEqual(["MOD_ME_1"], diff.get_modified_features())

# Everything must be sorted
        self.assertEqual(["ABC_1", "BAR_2", "FOO_1", "FOO_2", "MOD_ME_1"], diff.get_changed_features())


if __name__ == '__main__':
    t.main()
