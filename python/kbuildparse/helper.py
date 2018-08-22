""" Helper module for kbuildparse."""

# Copyright (C) 2014-2015 Andreas Ruprecht <andreas.ruprecht@fau.de>
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

import kbuildparse.data_structures as DataStructures

def build_precondition(input_list, additional=None):
    """ Build a DataStructures.Precondition object from a given @input_list.
    Additional constraints from @additional are added to the Precondition."""
    alternatives = []
    for alternative in input_list:
        string = " && ".join(alternative)
        if string != "":
            alternatives.append(string)
        else:
            # This case means that at least one unconditional path was found ->
            # return no condition.
            alternatives = []
            break

    alt_string = " || ".join(alternatives)

    ret = DataStructures.Precondition()
    if additional:
        ret.extend(additional)

    if len(alternatives) > 1:
        ret.add_condition("(" + alt_string + ")")
    elif len(alt_string) > 1:
        ret.add_condition(alt_string)

    return ret
