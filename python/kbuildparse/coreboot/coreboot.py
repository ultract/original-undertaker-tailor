""" Implementation of kbuildparse base classes for Coreboot."""

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

import collections
import logging
import os
import re

import kbuildparse.base_classes as BaseClasses
import kbuildparse.data_structures as DataStructures
import kbuildparse.helper as Helper
import kbuildparse.linux.linux as Linux
import vamos.tools as Tools
import vamos.golem.kbuild as Kbuild
import vamos.model as Model

CONFIG_FORMAT = Model.CONFIG_FORMAT
REGEX_IFNEQ = re.compile(r"\s*(ifneq|ifeq)\s+(.*)")
REGEX_IFNEQ_CONF = re.compile(r"\(\$\(" + CONFIG_FORMAT +
                              r"\),\s*(y|m|n|\s*)\s*\)")
REGEX_IFNDEF = re.compile(r"\s*(ifdef|ifndef)\s+(.*)")
REGEX_ENDIF = re.compile(r"\s*endif\s*")
REGEX_ELSE = re.compile(r"\s*else\s*")

class CorebootInit(BaseClasses.InitClass):
    """ Init class for Coreboot."""

    def __init__(self, model, arch):
        """ Constructor for CorebootInit, takes model and arch parameters."""
        super(CorebootInit, self).__init__(model, arch)

    def get_file_for_subdirectory(self, directory):
        """ Select the correct Kbuild makefile in directory."""
        if not directory.endswith('/'):
            directory += '/'
        return directory + "Makefile.inc"

    def process(self, parser, args, dirs_to_process):
        """ Initialize the global variables and find the subdirectories which
        we need to descend into by parsing the toplevel Makefile, looking for
        the classes-y and subdirs-y definitions."""

        # nesting unparseable expressions:
        parser.global_vars.create_variable("no_config_nesting", 0)

        # directory preconditions
        parser.global_vars.create_variable("dir_cond_collection",
            collections.defaultdict(DataStructures.Alternatives))

        parser.global_vars.create_variable("mainboard_dirs", [])

        for vendor in os.listdir("src/mainboard"):
            directory = "src/mainboard/" + vendor
            if not os.path.isdir(directory):
                continue
            for mainboard in os.listdir(directory):
                f = directory + "/" + mainboard
                if not os.path.isdir(f):
                    continue

                parser.global_vars["mainboard_dirs"].append(vendor + "/" + \
                                                            mainboard)

        with open(self.get_file_for_subdirectory("."), 'r') as mainfile:
            while True:
                (good, line) = Tools.get_multiline_from_file(mainfile)
                if not good:
                    break

                # evaluate classes-y
                match = re.match(r"^classes-y\s*:=\s*(.*)", line)
                if match:
                    classes = [x for x in re.split("\t| ", match.group(1)) if x]
                    parser.global_vars.create_variable("classes", classes)
                    continue

                # look for subdirs
                match = re.match(r"^subdirs-y\s*[:\+]=\s*(.*)", line)
                if not match:
                    continue

                subdirs = [x for x in re.split("\t| ", match.group(1)) if x]
                for item in subdirs:
                    if r"$(MAINBOARDDIR)" in item:
                        for mainboard_dir in parser.global_vars["mainboard_dirs"]:
                            subdir = re.sub(r"\$\(MAINBOARDDIR\)",
                                            mainboard_dir, item)
                            if os.path.isdir(subdir):
                                dirs_to_process[subdir] = DataStructures.Precondition()

                    elif r"$(ARCHDIR-y)" in line:
                        # FIXME: x86 hardcoded for testing tree
                        item = re.sub(r"\$\(ARCHDIR-y\)", r"x86", item)
                        precond = DataStructures.Precondition()
                        precond.add_condition("CONFIG_ARCH_X86")
                        parser.global_vars["dir_cond_collection"][item].\
                            add_alternative(precond)
                        dirs_to_process[item] = precond

                    elif os.path.isdir(item):
                        dirs_to_process[item] = DataStructures.Precondition()

        # User provided directories have no precondition
        for item in args.directory:
            dirs_to_process[item] = DataStructures.Precondition()

        # Initialize global data structure
        parser.global_vars.create_variable("file_features",
            collections.defaultdict(DataStructures.Alternatives))


class CorebootBefore(BaseClasses.BeforePass):
    """ Initialization of per-file variables for Coreboot."""

    def __init__(self, model, arch):
        """ Constructor for CorebootBefore, takes model and arch parameters"""
        super(CorebootBefore, self).__init__(model, arch)

    def process(self, parser, basepath):
        """ Initialize data structures before main processing loop."""
        # Updated with #if(n)def/#if(n)eq conditions
        parser.local_vars.create_variable("ifdef_condition",
            DataStructures.Precondition())

        parser.local_vars.create_variable("dir_cond_collection", [])

        parser.local_vars.create_variable("composite_map",
            collections.defaultdict(DataStructures.Alternatives))

        parser.local_vars.create_variable("definitions", {})

        logging.debug("In path: " + basepath)


class _00_CorebootDefinitions(Linux._00_LinuxDefinitions):

    def do_line_replacements(self, parser, line):
        # Replacement of defined macros
        changed = True
        while changed:
            changed = False
            for definition in parser.local_vars["definitions"]:
                if r"$(" + definition + r")" in line:
                    line = re.sub(r"\$\(" + definition + r"\)",
                                  parser.local_vars["definitions"][definition],
                                  line)
                    changed = True

        # Top level Makefile exports this equivalence
        line = re.sub(r"\$\(src\)", "src", line)

        return line

    def __init__(self, model, arch):
        super(_00_CorebootDefinitions, self).__init__(model, arch)


class _01_CorebootIf(Linux._01_LinuxIf):
    """ Evaluation of ifdef/ifeq conditions in Coreboot."""

    def __init__(self, model, arch):
        super(_01_CorebootIf, self).__init__(model, arch)


def generate_uppercase_string(inp):
    return inp.replace("-", "_").upper()


class _02_CorebootObjects(BaseClasses.DuringPass):
    """ Evaluation of lines describing object files in Coreboot."""

    def __init__(self, model, arch):
        super(_02_CorebootObjects, self).__init__(model, arch)

    def get_vendor_and_board_options_from(self, path):
        """ Return a tuple of the correct strings for the vendor
        and board configuration options for the given @path."""
        matcher = re.match(r"src\/mainboard\/(.*?)\/([^\/]+)\/*", path)
        if not matcher:
            return None

        vendor = generate_uppercase_string(matcher.group(1))
        board = generate_uppercase_string(matcher.group(2))

        return ("CONFIG_VENDOR_" + vendor,
                "CONFIG_BOARD_" + vendor + "_" + board)

    def process(self, parser, line, basepath):
        line = line.processed_line

        subdir = re.match(r"\s*subdirs-(y|\$[\{\(]" + CONFIG_FORMAT + \
                          r"[\}\)])\s*(:=|\+=|=)\s*(.*)", line)
        if subdir:
            matches = [x for x in re.split("\t| ", subdir.group(4)) if x]
            for match in matches:
                fullpath = os.path.relpath(basepath + "/" + match)
                tmp_condition = DataStructures.Precondition()

                if not subdir.group(1) == "y":
                    tmp_condition.add_condition("CONFIG_" + subdir.group(2))

                if os.path.isdir(fullpath):
                    additional_condition = []
                    # See below, this is not really Kbuild, but approximation to
                    # golem formulae
                    if basepath.startswith("src/mainboard/"):
                        (vendor_option, board_option) = \
                                self.get_vendor_and_board_options_from(basepath)

                        additional_condition = parser.local_vars["ifdef_condition"][:]
                        additional_condition.append(vendor_option)
                        additional_condition.append(board_option)

                    cond = Helper.build_precondition(
                                    [tmp_condition], Helper.build_precondition(
                                        parser.global_vars["dir_cond_collection"][basepath],
                                        additional_condition
                                    )
                                )

                    parser.global_vars["dir_cond_collection"][fullpath].\
                        add_alternative(cond)
                    if not fullpath in parser.local_vars["dir_cond_collection"]:
                        parser.local_vars["dir_cond_collection"].append(fullpath)

            return True

        cls = re.match(r"\s*classes-y\s*\+=\s*(.*)", line)
        if cls:
            parser.global_vars["classes"].extend(cls.group(1).split())

        for cls in parser.global_vars["classes"]:
            cls_match = re.match(cls + r"-(y|\$[\(\{]" + CONFIG_FORMAT +
                                 r"[\}\)]|srcs)\s*(:=|\+=|=)\s*(.*)", line)
            if not cls_match:
                continue

            matches = [x for x in re.split("\t| ", cls_match.group(4)) if x]
            for match in matches:
                fullpath = os.path.relpath(basepath + "/" + match)
                additional_condition = []

                if not cls_match.group(1) == "y" and not cls_match.group(1) == "srcs":
                    additional_condition.append("CONFIG_" + cls_match.group(2))

                # SONDERFALL: src/arch/x86/Makefile.inc
                if basepath == "src/arch/x86" and \
                        cls_match.group(1) == "srcs" and \
                        "$(MAINBOARDDIR)" in match:
                    for mbdir in parser.global_vars["mainboard_dirs"]:
                        cur_fullpath = re.sub(r"\$\(MAINBOARDDIR\)", mbdir, match)
                        sourcefile = Kbuild.guess_source_for_target(cur_fullpath)
                        if sourcefile:
                            # Information from directory can be converted
                            # into conditions. This is NOT in the Kbuild
                            # system but yields higher equivalence with
                            # golem.
                            (vendor_option, board_option) = \
                                    self.get_vendor_and_board_options_from(cur_fullpath)
                            condition = parser.local_vars["ifdef_condition"][:]
                            condition.append(vendor_option)
                            condition.append(board_option)

                            cond = Helper.build_precondition(
                                parser.global_vars["dir_cond_collection"][basepath],
                                condition)

                            new_alt = DataStructures.Alternatives()
                            new_alt.add_alternative(cond)
                            parser.global_vars["file_features"][cur_fullpath] = new_alt

                # Normalfall:
                additional_condition.extend(parser.local_vars["ifdef_condition"][:])

                # src/mainboard has conditions we know from the path...
                # Usually this is not in the build system, but can be used
                # for higher equivalence ratings against golem
                if basepath.startswith("src/mainboard/"):
                    (vendor_option, board_option) = \
                        self.get_vendor_and_board_options_from(fullpath)

                    additional_condition.append(vendor_option)
                    additional_condition.append(board_option)

                cond = Helper.build_precondition(
                    parser.global_vars["dir_cond_collection"][basepath],
                    additional_condition)

                sourcefile = Kbuild.guess_source_for_target(fullpath)
                if sourcefile:
                    new_alt = DataStructures.Alternatives()
                    new_alt.add_alternative(cond)
                    parser.global_vars["file_features"][fullpath] = new_alt
                else:
                    parser.local_vars["composite_map"][fullpath].add_alternative(
                        cond)

            return True

        return False


class _01_CorebootExpandMacros(BaseClasses.AfterPass):
    """ Expand macros in Coreboot Makefiles."""

    # Static strings/regexes
    regex_base = re.compile(r"\$\(([A-Za-z0-9,_-]+)\)")

    def __init__(self, model, arch):
        """ Constructor for _02_CorebootExpandMacros. """
        super(_01_CorebootExpandMacros, self).__init__(model, arch)

    def expand_macro(self, name, path, condition, already_expanded, parser):
        """ Expand a macro named @name. Preconditions to the folder are given
        in @condition. The path to the input file is @path and to avoid endless
        recursion processing is aborted if the current name is already present
        in @already_expanded. To save the results, the local variables are
        accessed via the @parser parameter."""

        if name in already_expanded:
            return

        already_expanded.add(name)

        basepath = os.path.dirname(name)
        filename = os.path.basename(name)

        match = re.match(self.regex_base, filename)
        if not match:
            return

        basename = match.group(1)

        scan_regex_string = r"\s*" + basename + r"\s*(:=|\+=|=)\s*(.*)"

        if not path in parser.file_content_cache:
            parser.read_whole_file(path)

        inputs = parser.file_content_cache[path]

        for line in inputs:

            if line.invalid:
                continue

            ifdef_condition = line.condition
            line = line.processed_line

            match = re.match(scan_regex_string, line)
            if not match:
                continue

            rhs = match.group(2)

            matches = [x for x in re.split("\t| ", rhs) if x]
            for item in matches:
                fullpath = basepath + "/" + item
                passdown_condition = condition[:]

                sourcefile = Kbuild.guess_source_for_target(fullpath)
                if not sourcefile:
                    self.expand_macro(fullpath, path, passdown_condition,
                                      already_expanded, parser)
                else:
                    full_condition = DataStructures.Precondition()
                    if len(condition) > 0:
                        full_condition = condition[:]
                    if len(ifdef_condition) > 0:
                        full_condition.extend(ifdef_condition)

                    parser.global_vars["file_features"][sourcefile].\
                        add_alternative(full_condition[:])

        already_expanded.discard(name)

    def process(self, parser, path, condition_for_current_dir):
        """ Process macros from composite_map variable. """
        # Macro expansion
        for obj in parser.local_vars["composite_map"]:
            downward_condition = Helper.build_precondition(parser.\
                                    local_vars["composite_map"][obj])
            already_expanded = set()

            self.expand_macro(obj, path, downward_condition,
                              already_expanded, parser)


class _02_CorebootProcessSubdirectories(BaseClasses.AfterPass):
    """ Process subdirectories in Coreboot."""

    def __init__(self, model, arch):
        """ Constructor for _02_CorebootProcessSubdirectories. """
        super(_02_CorebootProcessSubdirectories, self).__init__(model, arch)

    def process(self, parser, path, condition_for_current_dir):
        """ Process all subdirectories. """
        for directory in parser.local_vars["dir_cond_collection"]:
            downward_condition = Helper.build_precondition(
                parser.global_vars["dir_cond_collection"][directory],
                condition_for_current_dir)
            descend = parser.init_class.get_file_for_subdirectory(directory)
            parser.process_kbuild_or_makefile(descend, downward_condition)


class _03_CorebootOutput(BaseClasses.BeforeExit):
    """ Output class for Coreboot."""

    def __init__(self, model, arch):
        """ Constructor for _03_CorebootOutput. """
        super(_03_CorebootOutput, self).__init__(model, arch)

    def process(self, parser):
        """ Print conditions collected in file_features variable. """
        file_features = parser.global_vars["file_features"]

        for item in sorted(file_features):
            alternatives = []
            for alternative in file_features[item]:
                one_alternative = []

                # Add precondition for current item
                for condition in alternative:
                    if condition == "":
                        continue
                    one_alternative.append(condition)

                current = " && ".join(one_alternative)
                if not current:
                    continue
                elif len(file_features[item]) > 1 and len(one_alternative) > 1:
                    alternatives.append("(" + current + ")")
                else:
                    alternatives.append(current)

            full_string = " || ".join(alternatives)
            filename = Kbuild.normalize_filename(os.path.relpath(item))

            if full_string:
                print "FILE_" + filename + " \"" + full_string + "\""
            else:
                print "FILE_" + filename
