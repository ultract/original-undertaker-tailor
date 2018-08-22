# Copyright (C) 2014 Andreas Ruprecht <rupran@einserver.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

#!/usr/bin/env python2

import subprocess
import sys
import os

import unittest2 as t

class Testcase(t.TestCase):

    def test_minigolem(self):
        os.chdir("validation-minigolem/")
        p = subprocess.Popen(["../minigolem", "--check", "."],
                            stdout=subprocess.PIPE)
        exitcode = p.wait()
        assert(exitcode == 0)

        fd = open("preconditions.ref")
        for actual in p.stdout:
            expected = fd.readline()
            if not actual == expected:
                print "Differing output!"
                print "Expected: " + expected
                print "Actual:   " + actual
                sys.exit(1)
#            assert(line == fd.readline())

if __name__ == "__main__":
    t.main()


