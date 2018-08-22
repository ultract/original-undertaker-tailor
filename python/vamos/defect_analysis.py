
"""Utilities to detect and analyze defects in a given source file."""

# Copyright (C) 2014-2015 Valentin Rothberg <valentinrothberg@gmail.com>
# Copyright (C) 2015 Andreas Ruprecht <andreas.ruprecht@fau.de>

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


import re
import os
import tempfile
import vamos.tools as tools
import vamos.golem.kbuild as kbuild
from vamos.block import Block
from vamos.model import find_similar_symbols

from collections import defaultdict

def defect_analysis(srcfile, models, flag=""):
    """Defect analysis using the Undertaker tool.
    Returns list of defect reports."""
    reports = []
    defect_pattern = re.compile(r"[\S]+\.[cSh]\.B[0-9]+[\S]+")
    (output, _) = tools.execute("undertaker -v -m %s %s %s" %
                                (models, srcfile, flag), failok=True)
    for report in output:
        if not report.startswith("I:"):
            continue
        matches = defect_pattern.findall(report)
        if matches:
            defect = matches[0].strip()
            reports.append(defect)
    return reports


def batch_analysis(srclist, models, flags=""):
    """Batch defect analysis of files in @srclist. Assign defects to the blocks
    of the files and return a dictionary {file: [blocks]}."""
    # make a temporary batchfile
    batchfile = tempfile.mkstemp()[1]
    with open(batchfile, "w") as stream:
        for srcfile in srclist:
            stream.write("%s\n" % srcfile)

    # parse blocks for each source files
    blocks = {}
    for srcfile in srclist:
        blocks[srcfile] = Block.parse_blocks(srcfile)

    # defect analysis and assignment of defects to each source file
    flags += " -b %s" % batchfile
    for report in defect_analysis("", models, flags):
        bid = Block.get_block_id(report)
        bfile = Block.get_block_file(report)
        # assign information to the blocks of the source file
        srcblocks = blocks[bfile]
        if report.endswith(".mus"):
            srcblocks[bid].mus = report
            # remove the '.mus' suffix from the defect report
            bdefect = Block.get_block_defect(report[:-len('.mus')])
        else:
            bdefect = Block.get_block_defect(report)
        srcblocks[bid].defect = bdefect

    for srcfile in blocks:
        blocks[srcfile] = list(blocks[srcfile].values())  # dict to list

    os.remove(batchfile)
    return blocks


def compare_blocks(blocks_a, blocks_b):
    """Compare both lists of blocks to detect if a defect is introduced,
    repaired, changed or unchanged. Return a sorted list of defect affected
    blocks."""
    defects = []

    for block_a in blocks_a:
        for block_b in blocks_b:
            if Block.matchrange(block_a, block_b):
                block_a.match = block_b
                block_b.match = block_a

    for block_b in [b for b in blocks_b if not b.match and b.is_defect()]:
        block_b.report = "\nNew defect: %s" % block_b
        defects.append(block_b)

    for block_a in blocks_a:
        block_b = block_a.match

        # We did not find a match
        if not block_b:
            if block_a.is_defect():
                block_a.report = "\nDefect repaired (removed): %s" % block_a
                defects.append(block_a)
        # We found a match, and only block_b is a defect -> introduced
        elif not block_a.is_defect() and block_b.is_defect():
            block_b.report = "\nNew defect: %s" % block_b
            defects.append(block_b)
        # Again a match, but only block_a is a defect -> repaired
        elif block_a.is_defect() and not block_b.is_defect():
            block_a.report = "\nDefect repaired: %s" % block_a
            defects.append(block_a)
        # Match, block_a and block_b are the same defect class
        # Note: Here, either both block_a and block_b are defect or
        #       both are not defect
        elif block_a.defect == block_b.defect and block_a.is_defect():
            block_b.report = "\nUnchanged defect: %s" % block_b
            defects.append(block_b)
        # Match, block_a and block_b have different defect classes
        # Note: we also reach this case if both block_a and block_b are not
        #       defect, but then the check fails so we don't do anything
        elif block_a.defect != block_b.defect:
            block_b.report = "\nChanged defect FROM: %s" % block_a
            block_b.report += "\n                 TO: %s" % block_b
            defects.append(block_b)

    return Block.sort(defects)


def in_models(feature, models, arch=""):
    """Check if the feature is defined in at least one of the models or in the
    model of the specified architecture."""
    if arch:
        for model in models:
            if re.search(r"\/%s\.model$" % arch, model.path):
                return model.is_defined(feature)
    for model in models:
        if model.is_defined(feature):
            return True
    return False


def check_missing_defect(block, mainmodel, models, arch=""):
    """Check the missing defect and extend its defect report."""
    missing_found = False

    for item in block.get_transitive_items(mainmodel):
        if in_models(item, models, arch):
            # filter architecture dependent features to avoid false positives
            continue
        missing_found = True
        if item in block.ref_items:
            block.report += "\n\t%s is referenced but not defined in Kconfig" \
                            % item
        else:
            block.report += "\n\t%s is in dependencies but not defined in " \
                            "Kconfig" % item
        sims = find_similar_symbols(item, mainmodel)
        block.report += "\n\n\tSimilar symbols: %s" % ', '.join(sims)

    if missing_found:
        return

    # this should not happen
    block.report += "\n\tcould not detect cause of defect"


def check_kbuild_defect(block, models):
    """Check the kbuild defect and extend the defect report. Currently, the
    file precondition from the build system as well as the presence condition for
    the analysed block are printed. This could be misleading as the error could
    be in the transitive dependencies of the file precondition."""

    reason = "contradiction"
    if "undead" in block.defect:
        reason = "tautology"

    block.report += "\n\tFile preconditions from build system create" \
                    " a %s" % (reason)

    fp_var = "FILE_" + kbuild.normalize_filename(block.srcfile)
    fp_dict = defaultdict(list)
    for model in models:
        if model.is_defined(fp_var):
            fp_dict[model[fp_var]].append(model.arch)

    if fp_dict:
        for condition in fp_dict:
            arch_string = "architecture"
            if len(fp_dict[condition]) > 1:
                arch_string += "s"
            block.report += "\n\n\tFile precondition for %s %s: %s" % \
                            (arch_string, str(sorted(fp_dict[condition])),
                             condition)

    # Do not check block conditions for block B00
    if block.range[0] != 0:
        block.report += "\n\n\tBlock has the following preconditions:"
        for condition in block.precondition:
            block.report += "\n\t%s" % condition

    if reason == "tautology":
        block.report += "\n\n\tNote: If the file precondition and block"      \
                        " conditions do not directly show a tautology, the"   \
                        " dependencies of features referenced in the file"    \
                        " preconditions need to be checked."
    else:
        block.report += "\n\n\tNote: If the file precondition and block"      \
                        " conditions are not contradictory, their respective" \
                        " constraints need to be checked. In this case,"      \
                        " consider running undertaker-checkpatch again with"  \
                        " \"--mus\" to identify the symbol causing the defect."


def check_kconfig_defect(block, model):
    """Check the kconfig defect and extend its defect report. This function only
    covers the trivial case of a kconfig defect being caused by referencing
    always_on or always_off items.

    Note: always_{on, off} items do not always contribute to the
    contradictory formula, and should thereby only be seen as indicators of a
    defect's cause. Oftentimes, manual analysis of the minimal unsatisfiable
    subformula (see undertaker --mus) is required."""

    for item in block.get_transitive_items(model):
        if item in model.always_on_items:
            if item in block.ref_items:
                block.report += "\n\t%s is referenced and always on" % item
            else:
                block.report += "\n\t%s is in dependencies and always on" \
                                % item
        elif item in model.always_off_items:
            if item == "CONFIG_COMPARE_WITH_NONEXISTENT":
                continue
            if item in block.ref_items:
                block.report += "\n\t%s is referenced and always off" % item
            else:
                block.report += "\n\t%s is in dependencies and always off" \
                                % item

    block.report += "\n\n\tBlock has the following preconditions:"
    for condition in block.precondition:
        block.report += "\n\t%s" % condition


def check_code_defect(block):
    """Check the code defect and extend its defect report."""
    # report the block's boolean precondition
    reason = "Contradiction"
    if "undead" in block.defect:
        reason = "Tautology"
    block.report += "\n\t%s in the block's precondition:" % reason

    for cond in block.precondition:
        block.report += "\n\t%s" % cond

    cpp_items = []

    # find previously defined CPP items (e.g., #define CONFIG_)
    (output, _) = tools.execute(r"git grep -n '^\s*#def' %s" % block.srcfile)
    for out in output:
        feature = tools.get_kconfig_items(out)
        if feature and feature[0] in block.ref_items:
            cpp_items.append(out)

    # find previously undefined CPP items (e.g., #undefine CONFIG_)
    (output, _) = tools.execute(r"git grep -n '^\s*#undef' %s" % block.srcfile)
    for out in output:
        feature = tools.get_kconfig_items(out)
        if feature and feature[0] in block.ref_items:
            cpp_items.append(out)

    if cpp_items:
        block.report += "\n\n\tThe following lines of source code may cause "
        block.report += "the defect:"
        for item in sorted(cpp_items):
            block.report += "\n\t\t%s" % item
