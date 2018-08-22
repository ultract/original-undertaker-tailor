
"""vamos - common auxiliary model related functionality"""

# Copyright (C) 2011-2012 Christian Dietrich <christian.dietrich@informatik.uni-erlangen.de>
# Copyright (C) 2011-2012 Reinhard Tartler <tartler@informatik.uni-erlangen.de>
# Copyright (C) 2014 Stefan Hengelein <stefan.hengelein@fau.de>
# Copyright (C) 2014 Andreas Ruprecht <rupran@einserver.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from vamos.rsf2model.RsfReader import ItemRsfReader, RsfReader

import difflib
import logging
import re
import os

CONFIG_FORMAT = r"CONFIG_([A-Za-z0-9_-]+)"

def get_model_for_arch(arch):
    """
    Returns an cnf or rsf model for the given architecture
    Return 'None' if no model is found.
    """
    for p in ("models/%s.cnf", "models/%s.model"):
        if os.path.exists(p % arch):
            return p % arch

    return None


def parse_model(path, shallow=False):
    if path.endswith('.cnf'):
        return CnfModel(path)
    return RsfModel(path, shallow=shallow)


def find_similar_symbols(symbol, model):
    """Return a list of max. three Kconfig symbols in %model that are
    string-similar to %symbol."""
    return difflib.get_close_matches(symbol, model.keys())


class RsfModel(dict):
    def __init__(self, path, rsf=None, readrsf=True, shallow=False):
        # pylint: disable=R0204
        dict.__init__(self)
        self.path = path
        self.always_on_items = set()
        self.always_off_items = set()

        with open(path) as fd:
            self.parse(fd)

        if not rsf and path.endswith(".model"):
            rsf = path[:-len(".model")] + ".rsf"
            self.arch = os.path.basename(path)[:-len(".model")]

        if readrsf and rsf:
            try:
                with open(rsf) as f:
                    if shallow:
                        self.rsf = ItemRsfReader(f)
                    else:
                        self.rsf = RsfReader(f)
            except IOError:
                logging.warning("no rsf file for model %s was found", path)

    def parse(self, fd):
        counter = 0
        lines = fd.readlines()
        # read the meta data
        for line in lines:
            line = line.strip()
            if line.startswith("UNDERTAKER_SET"):
                line = line.split(" ")[1:]
                if line[0] == "ALWAYS_ON":
                    always_on_items = [l.strip(" \t\"") for l in line[1:]]
                    self.always_on_items.update(always_on_items)
                elif line[0] == "ALWAYS_OFF":
                    always_off_items = [l.strip(" \t\"") for l in line[1:]]
                    self.always_off_items.update(always_off_items)
            elif line.startswith("I:"):
                pass
            else:
                break

            counter += 1

        # read the actual "symbol -> condition" pairs unconditionally
        while counter < len(lines):
            line = lines[counter].strip().split(" ", 1)
            counter += 1
            if len(line) == 1:
                self[line[0]] = None
            else:
                self[line[0]] = line[1].strip(" \"\t\n")

    def mentioned_items(self, key):
        """
        @return list of mentioned items of the key's implications
        """
        expr = self.get(key, "")
        if expr == None:
            return []
        expr = re.split("[()&!|><-]", expr)
        expr = [x.strip() for x in expr]
        return [x for x in expr if len(x) > 0]

    def leaf_features(self):
        """
        Leaf features are feature that aren't mentioned anywhere else

        @return list of leaf features in model
        """

        # Dictionary of mentioned items
        features = dict([(key, False) for key in self.keys()
                        if not key.endswith("_MODULE")])
        for key in features.keys():
            items = self.mentioned_items(key)
            items += self.mentioned_items(key + "_MODULE")
            for mentioned in items:
                # Strip _MODULE POSTFIX
                if mentioned.endswith("_MODULE"):
                    mentioned = mentioned[:-len("_MODULE")]

                # A Leaf can't "unleaf" itself. This is important for
                # circular relations like:
                #
                # CONFIG_A -> !CONFIG_A_MODULE
                # CONFIG_A_MODULE -> !CONFIG_A
                if key != mentioned and mentioned in features:
                    features[mentioned] = True
        return sorted([key for key in features if features[key] == False])

    def get_type(self, symbol):
        """
        RuntimeError gets raised if no corresponding rsf is found.
        @return data type of symbol.
        """
        if not self.rsf:
            raise RuntimeError("No corresponding rsf file found.")
        if symbol.startswith("CONFIG_"):
            symbol = symbol[len("CONFIG_"):]
        return self.rsf.get_type(symbol)


    def is_bool_tristate(self, symbol):
        """
        Returns true if symbol is bool or tristate, otherwise false is returned.

        Raises RuntimeError if no corresponding rsf-file is found.
        """

        if not self.rsf:
            raise RuntimeError("No corresponding rsf file found.")

        if symbol.startswith("CONFIG_"):
            symbol = symbol[len("CONFIG_"):]

        return self.rsf.is_bool_tristate(symbol)

    def slice_symbols(self, initial):
        """
        Apply the slicing algorithm to the given set of symbols
        returns a list of interesting symbol
        """
        if type(initial) == list:
            stack = initial
        else:
            stack = [initial]

        visited = set()

        while len(stack) > 0:
            symbol = stack.pop()
            visited.add(symbol)
            for new_symbols in self.mentioned_items(symbol):
                if not new_symbols in visited:
                    stack.append(new_symbols)
        return list(visited)

    def is_defined(self, feature):
        """
        Return true if feature is defined in the model.
        """
        return feature in self.keys()


class CnfModel(dict):
    def __init__(self, path):
        dict.__init__(self)
        self.path = path
        self.always_on_items = set()
        self.always_off_items = set()

        with open(path) as fd:
            self.parse(fd)

    def parse(self, fd):
        for line in fd:
            # we only need symbol information, stop when cnf formula starts
            if line.startswith("p cnf"):
                break

            if line.startswith("c sym "):
                line_split = line.split()
                sym = "CONFIG_" + line_split[2]
                code = int(line_split[3])
                self[sym] = code
                # tristate symbols also have a _MODULE sister
                if code == 2:
                    self[sym + '_MODULE'] = code

            elif line.startswith("c meta_value "):
                line_split = line.split()
                if line_split[2] == 'ALWAYS_ON':
                    self.always_on_items.update(line_split[3:])
                elif line_split[2] == 'ALWAYS_OFF':
                    self.always_off_items.update(line_split[3:])

    def get_type(self, symbol):
        """
        @raises RuntimeError if type code is unknown.
        @return data type of symbol or None if the symbol is missing.
        """
        if not symbol.startswith("CONFIG_"):
            symbol = "CONFIG_" + symbol

        if not symbol in self:
            return None

        code = {1 : 'boolean', 2 : 'tristate', 3 : 'integer',
                4 : 'hex', 5 : 'string', 6 : 'other'}
        if self[symbol] not in code:
            raise RuntimeError("Unknown type code code %d" % self[symbol])
        else:
            return code[self[symbol]]


    def is_bool_tristate(self, symbol):
        """
        @return True if symbol is tristate or boolean, otherwise False (other
        type or symbol not known)
        """

        if not symbol.startswith("CONFIG_"):
            symbol = "CONFIG_" + symbol

        if not symbol in self:
            return False

        code = self[symbol]
        return code == 1 or code == 2
