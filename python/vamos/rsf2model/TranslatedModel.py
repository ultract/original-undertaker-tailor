
"""rsf2model - extracts presence implications from kconfig dumps"""

# Copyright (C) 2011 Christian Dietrich <christian.dietrich@informatik.uni-erlangen.de>
# Copyright (C) 2014-2015 Stefan Hengelein <stefan.hengelein@fau.de>
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
#

from vamos.rsf2model import tools
from vamos.rsf2model.RsfReader import Choice
from vamos.rsf2model import BoolRewriter
from vamos.rsf2model.helper import BoolParserException


class TranslatedModel(tools.UnicodeMixin):
    def __init__(self, rsf):
        tools.UnicodeMixin.__init__(self)

        self.symbols = []
        self.deps = {}
        # mapping: key-symbol is selected by a list of options [symbol1, symbol2]
        self.selectedBy = {}

        self.always_on = set()
        self.always_off = set()

        self.rsf = rsf
        for option in self.rsf.options().values():
            self.translate_option(option)

        for option in self.rsf.options().values():
            if type(option) == Choice:
                self.translate_choice(option)

        for (item, default_set) in self.rsf.collect("Default", 0, True).items():
            option = self.rsf.options().get(item, None)
            if option:
                for default in default_set:
                    try:
                        self.translate_default(option, default)
                    except BoolParserException:
                        # Parsing expression failed, just ignore it
                        pass

        for (item, select_set) in self.rsf.collect("ItemSelects", 0, True).items():
            option = self.rsf.options().get(item, None)
            if option:
                for select in select_set:
                    try:
                        self.translate_select(option, select)
                    except BoolParserException:
                        # Parsing of a substring failed, just ignore it
                        pass

        if self.rsf.has_ignored_symbol:
            self.symbols.append("CONFIG_CADOS_IGNORED")

        if self.rsf.has_compare_with_nonexistent:
            self.symbols.append("CONFIG_COMPARE_WITH_NONEXISTENT")
            self.always_off.add("CONFIG_COMPARE_WITH_NONEXISTENT")

    def translate_option(self, option):
        # Generate symbols
        symbol = option.symbol()
        self.symbols.append(symbol)
        self.deps[symbol] = []
        self.selectedBy[symbol] = []

        if option.omnipresent():
            self.always_on.add(option.symbol())

        if option.tristate():
            symbol_module = option.symbol_module()
            self.symbols.append(symbol_module)
            self.deps[symbol_module] = []

            # mutual exclusion for tristate symbols
            self.deps[symbol].append("!%s" % symbol_module)
            self.deps[symbol_module].append("!%s" % symbol)
            self.deps[symbol_module].append("CONFIG_MODULES")

            # Add dependency

            # For tristate symbols (without _MODULE) the dependency must evaluate to y
            dep = option.dependency(eval_to_module = False)
            if dep:
                self.deps[symbol].insert(0, dep)

            # for _MODULE also "m" is ok
            dep = option.dependency(eval_to_module = True)
            if dep:
                self.deps[option.symbol_module()].insert(0, dep)
        else:
            dep = option.dependency(eval_to_module = True)
            if dep:
                self.deps[symbol].insert(0, dep)

    def translate_choice(self, choice):
        for (symbol, dep) in choice.insert_forward_references().items():
            self.deps[symbol].extend(dep)

    def translate_default(self, option, dependency):
        # dependency: [state, if <expr>]
        if len(dependency) != 2:
            return

        if type(option) == Choice or option.tristate() or option.prompts() != 0:
            return

        [state, cond] = dependency
        # don't try to translate defaults with empty string as value
        if state == '':
            return

        if state == "y" and cond == "y" \
                        and not option.has_depends():
            self.always_on.add(option.symbol())
            # we add a free item to the 'selectedBy' list. this is
            # important in the following scenario:
            # 1. Item ist default on
            # 2. item is selected by other item
            # 3. without the free item it is implied, that the second
            #    item is on, but with default to y this isn't right
            #
            # Difference:
            # A DEPS && (SELECT1)
            # A DEPS && (__FREE__ || SELECT1)
            self.selectedBy[option.symbol()].append(tools.new_free_item())
        elif state == "y" or cond == "y":
            if state == "y":
                expr = cond
            else:
                expr = state

            if expr == "n":
                # don't create pointless CONFIG_n entries
                return
            elif expr == "y" and not "CONFIG_y" in self.symbols:
                self.symbols.append("CONFIG_y")

            expr =  str(BoolRewriter.BoolRewriter(self.rsf, expr, eval_to_module = True).rewrite())
            self.selectedBy[option.symbol()].append(expr)
        # Default FOO "BAR" "BAZ"
        elif len(state) > 1 and len(cond) > 1:
            expr =  str(BoolRewriter.BoolRewriter(self.rsf, "(%s) && (%s)" % (state, cond),
                                                  eval_to_module = True).rewrite())
            self.selectedBy[option.symbol()].append(expr)


    def translate_select(self, option, select):
        #pylint: disable=R0912
        """
        @param option the option that declares the 'select' verb
        @param select: the option that is unconditionally selected (if option is selected)

        select is a tuple of (selected, condition)
        """
        if type(option) == Choice:
            return

        if len(select) != 2:
            return

        (selected, expr) = select

        selected = self.rsf.options().get(selected, None)
        if not selected:
            return

        # We only look on boolean selected options
        if type(selected) == Choice or selected.tristate():
            return

        imply = selected.symbol()

        if expr == "y":
            # select foo if y
            self.deps[option.symbol()].append(selected.symbol())
        else:
            # select foo if expr
            expr = str(BoolRewriter.BoolRewriter(self.rsf, expr, eval_to_module = True).rewrite())
            if expr != "":
                imply = "((%s) -> %s)" %(expr, selected.symbol())

            self.deps[option.symbol()].append(imply)

        if selected.prompts() == 0:
            self.selectedBy[selected.symbol()].append(option.symbol())

        if option.tristate():
            if selected.prompts() == 0:
                self.selectedBy[selected.symbol()].append(option.symbol_module())
            self.deps[option.symbol_module()].append(imply)


    def __unicode__(self):
        result = []
        result.append(u"I: Items-Count: %d\n" % len(self.symbols))
        result.append(u"I: Format: <variable> [presence condition]\n")
        result.append("UNDERTAKER_SET SCHEMA_VERSION 1.1\n")

        if len(self.always_on) > 0:
            result.append("UNDERTAKER_SET ALWAYS_ON "
                          + (" ".join(['"' + x + '"' for x in sorted(self.always_on)]))
                          + "\n")

        if len(self.always_off) > 0:
            result.append("UNDERTAKER_SET ALWAYS_OFF "
                          + (" ".join(['"' + x + '"' for x in sorted(self.always_off)]))
                          + "\n")

        for symbol in sorted(self.symbols):
            expression = ""
            deps = self.deps.get(symbol, [])
            if symbol in self.selectedBy and len(self.selectedBy[symbol]) > 0:
                dS = self.selectedBy[symbol]
                deps.append("(" + " || ".join(dS) + ")")

            expression = " && ".join(deps)
            if expression == "":
                result.append("%s\n" % symbol)
            else:
                result.append("%s \"%s\"\n" % (symbol, expression))
        return "".join(result)
