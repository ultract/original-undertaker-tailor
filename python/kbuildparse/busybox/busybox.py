""" Implementation of kbuildparse base classes for Busybox."""

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

class BusyboxInit(Linux.LinuxInit):
    """ Init class for Busybox."""

    def __init__(self, model, arch):
        """ Constructor for BusyboxInit, takes model and arch parameters."""
        super(BusyboxInit, self).__init__(model, arch)

    def process(self, parser, args, dirs_to_process):
        """ For Busybox, we need to generate the full Makefiles before parsing
        them by running 'make gen_build_files'. Additionally, initialize the
        list of top-level directories."""

        # Prepare tree to contain processed Kbuild files
        Tools.execute("make gen_build_files", failok=False)

        parser.global_vars.create_variable("no_config_nesting", 0)

        if len(args.directory) > 0:
            # User provided directories have no precondition
            for item in args.directory:
                dirs_to_process[item] = DataStructures.Precondition()
        else:
            # Default directories have no precondition. Find them by parsing the
            # top-level Makefile for a line starting with "libs-y :=" which does
            # not contain $(libs-y1) (i.e. don't consider the internal lists
            # which are constructed to call patsubst on etc.)
            with open(self.get_file_for_subdirectory("."), "r") as infile:
                while True:
                    (good, line) = Tools.get_multiline_from_file(infile)
                    if not good:
                        break
                    if line.startswith("libs-y\t") and not "$(libs-y1)" in line:
                        subdirs = [x for x in line.split() if x]
                        # Drop the first two tokens ("libs-y" and "+=") and
                        # initialize the dictionary with the remaining ones.
                        for subdir in subdirs[2:]:
                            dirs_to_process[subdir] = DataStructures.Precondition()
                        break


class BusyboxBefore(Linux.LinuxBefore):
    """ Initialization of per-file variables for Busybox."""

    def __init__(self, model, arch):
        """ Constructor for BusyboxBefore, takes model and arch parameters"""
        super(BusyboxBefore, self).__init__(model, arch)

    def process(self, parser, basepath):
        """ Initialize data structures before main processing loop."""

        # Initialize common variables from Linux parser
        super(BusyboxBefore, self).process(parser, basepath)

        # Special variable for archival/libarchive/
        if basepath == "archival/libarchive":
            parser.local_vars.create_variable("all_configs", [])


class _01_BusyboxIf(BaseClasses.DuringPass):
    """ Evaluation of ifdef/ifeq conditions in Busybox."""

    def __init__(self, model, arch):
        super(_01_BusyboxIf, self).__init__(model, arch)

    def process(self, parser, line, basepath):
        # Hacky bit for archival/libarchive/ -> these last 3 lines:
        # ifneq ($(lib-y),)
        # lib-y += $(COMMON_FILES)
        # endif
        # depend on information gathered depending on the concrete value of
        # configuration options during the build process. To successfully parse
        # them without that knowledge, let's ignore the surrounding
        # ifneq/endifs.
        if basepath == "archival/libarchive":
            if line == "ifneq ($(lib-y),)" or line == "endif":
                return True


class _02_BusyboxObjects(BaseClasses.DuringPass):
    """ Evaluation of lines describing object files in Busybox."""

    obj_line = r"\s*(core|lib)-(y|\$[\(\{]" + CONFIG_FORMAT + \
               r"[\)\}])\s*(:=|\+=|=)\s*(([A-Za-z0-9.,_\$\(\)/-]+\s*)+)"
    regex_obj = re.compile(obj_line)

    def __init__(self, model, arch):
        super(_02_BusyboxObjects, self).__init__(model, arch)

    def process(self, parser, line, basepath):

        line = line.processed_line

        regex_match = re.match(self.regex_obj, line)
        if not regex_match:
            return False

        rhs = regex_match.group(5)
        # First, check for match on core/lib/libs-y
        if regex_match.group(2) == "y":
            matches = [x for x in re.split("\t| ", rhs) if x]
            for match in matches:
                fullpath = basepath + "/" + match
                if os.path.isdir(fullpath):
                    parser.local_vars["dir_cond_collection"][fullpath].\
                        add_alternative(parser.local_vars["ifdef_condition"][:])
                else:
                    sourcefile = Kbuild.guess_source_for_target(fullpath)
                    if sourcefile:
                        parser.local_vars["file_features"][sourcefile].\
                            add_alternative(parser.local_vars["ifdef_condition"][:])
                    else:
                        parser.local_vars["composite_map"][fullpath].\
                            add_alternative(parser.local_vars["ifdef_condition"][:])
        else:
            # Then test obj-$(CONFIG_XY)
            config = regex_match.group(3)

            condition = Tools.get_config_string(config, self.model)

            matches = [x for x in re.split("\t| ", rhs) if x]

            parser.local_vars["ifdef_condition"].add_condition(condition)

            for match in matches:
                fullpath = basepath + "/" + match
                if os.path.isdir(fullpath):
                    parser.local_vars["dir_cond_collection"][fullpath].\
                        add_alternative(parser.local_vars["ifdef_condition"][:])
                else:
                    # Hacky bit for COMMON_FILES in this directory
                    if basepath == "archival/libarchive":
                        parser.local_vars["all_configs"].append(condition)
                    sourcefile = Kbuild.\
                        guess_source_for_target(fullpath)
                    if sourcefile:
                        parser.local_vars["file_features"][sourcefile].\
                            add_alternative(parser.local_vars["ifdef_condition"][:])
                    else:
                        parser.local_vars["composite_map"][fullpath].\
                            add_alternative(parser.local_vars["ifdef_condition"][:])

            parser.local_vars["ifdef_condition"].pop()
        return True


class _01_BusyboxExpandMacros(BaseClasses.AfterPass):
    """ Expand macros in Busybox Makefiles."""

    # Static strings/regexes
    regex_base = re.compile(r"([A-Za-z0-9,_-]+)\.o|\$\(([A-Za-z0-9,_-]+)\)")

    def __init__(self, model, arch):
        """ Constructor for _01_BusyboxExpandMacros. """
        super(_01_BusyboxExpandMacros, self).__init__(model, arch)

    def expand_macro(self, name, path, condition, already_expanded, parser):
        """ Expand the macro @name. Preconditions to the folder are given
        in @condition. The path to the input file is @path and to avoid endless
        recursion processing is aborted if the current name is already present
        in @already_expanded. To save the results, the local variables are
        accessed via the @parser parameter."""

        if name in already_expanded:
            return

        already_expanded.add(name)

        ifdef_condition = DataStructures.Precondition()
        basepath = os.path.dirname(name)
        filename = os.path.basename(name)

        basename = ""

        match = re.match(self.regex_base, filename)
        if not match:
            return

        if match.group(1) is None:  # we have a macro
            basename = match.group(2)
            if basename.endswith("y"):
                basename = basename[:-1]
        elif match.group(2) is None:  # we have a file
            basename = match.group(1)

        # Hacky bit for archival/libarchive/
        if "all_configs" in parser.local_vars and basename == "COMMON_FILES":
            ifdef_condition.add_condition(" || ".join(parser.local_vars["all_configs"]))

        scan_regex_string = ""
        if match.group(1) is None:
            scan_regex_string = r"\s*" + basename + r"(|y|\$\(" + \
                                CONFIG_FORMAT + r"\))\s*(:=|\+=|=)\s*(.*)"
        else:
            scan_regex_string = r"\s*" + basename + r"(|-y|-objs|-\$\(" + \
                                CONFIG_FORMAT + r"\))\s*(:=|\+=|=)\s*(.*)"

        if not path in parser.file_content_cache:
            parser.read_whole_file(path)

        inputs = parser.file_content_cache[path]

        for line in inputs:

            line = line.processed_line

            match = re.match(scan_regex_string, line)
            if not match:
                continue

            config_in_composite = match.group(2)
            condition_comp = ""
            if config_in_composite:
                condition_comp = \
                    Tools.get_config_string(config_in_composite,
                                            self.model)

            rhs = match.group(4)

            matches = [x for x in re.split("\t| ", rhs) if x]
            for item in matches:
                fullpath = basepath + "/" + item
                passdown_condition = condition[:]
                if config_in_composite:
                    passdown_condition.append(condition_comp)

                if os.path.isdir(fullpath):
                    parser.local_vars["dir_cond_collection"]\
                        [fullpath].add_alternative(passdown_condition[:])
                else:
                    sourcefile = Kbuild.guess_source_for_target(fullpath)
                    if not sourcefile:
                        self.expand_macro(fullpath, path,
                                          passdown_condition,
                                          already_expanded, parser)
                    else:
                        full_condition = DataStructures.Precondition()
                        if len(condition) > 0:
                            full_condition = condition[:]
                        if config_in_composite:
                            full_condition.append(condition_comp)
                        if len(ifdef_condition) > 0:
                            for ifdef_cond in ifdef_condition:
                                full_condition.append(ifdef_cond)

                        parser.local_vars["file_features"][sourcefile].\
                            add_alternative(full_condition[:])

        already_expanded.discard(name)

    def process(self, parser, path, condition_for_current_dir):
        """ Process macros from composite_map variable. """
        # Macro expansion
        for obj in parser.local_vars.get_variable("composite_map"):
            downward_condition = Helper.build_precondition(parser.\
                                    local_vars["composite_map"][obj])
            already_expanded = set()

            self.expand_macro(obj, path, downward_condition, already_expanded,
                              parser)


class _02_BusyboxProcessSubdirectories(Linux._02_LinuxProcessSubdirectories):
    """ Process subdirectories in Busybox."""

    def __init__(self, model, arch):
        """ Constructor for _02_BusyboxProcessSubdirectories. """
        super(_02_BusyboxProcessSubdirectories, self).__init__(model, arch)


class _03_BusyboxOutput(Linux._03_LinuxOutput):
    """ Output class for Busybox."""

    def __init__(self, model, arch):
        """ Constructor for _03_BusyboxOutput. """
        super(_03_BusyboxOutput, self).__init__(model, arch)
