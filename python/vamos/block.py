
"""Utilities for conditional CPP blocks."""

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
import whatthepatch
import itertools
import vamos.tools as tools
import vamos.golem.kbuild as kbuild

#pylint: disable=R0902

class Block(object):
    """Represents a conditional block."""
    def __init__(self, srcfile):
        object.__init__(self)
        self.srcfile = srcfile
        self.bid = ""
        self.range = (0, 0)
        self.new_range = (0, 0)
        # defect related data
        self.defect = "no_defect"
        self.report = ""
        self.match = None
        self.ref_items = set()
        self.mus = ""  # path to the MUS report
        self.precondition = []

    def update_range(self, pos, value):
        """Update the block's ranges with respect to the given position."""
        if value < 0:
            # Deleted lines are relative to the original file...
            start_range = self.range[0]
            end_range = self.range[1]
        else:
            # ...but inserted lines are relative to the updated file
            start_range = self.new_range[0]
            end_range = self.new_range[1]

        if pos <= start_range:
            self.new_range = (self.new_range[0] + value, self.new_range[1])
        if pos <= end_range:
            self.new_range = (self.new_range[0], self.new_range[1] + value)

    def __str__(self):
        """To string method of block."""
        return self.srcfile + ":" \
                + self.bid + ":" \
                + str(self.range[0]) + ":" \
                + str(self.range[1]) + ":" \
                + self.defect

    def is_defect(self):
        """Return True if the block is a defect, hence it needs to be global and
        not a no_kconfig defect."""
        return "globally" in self.defect and not "no_kconfig" in self.defect

    def get_transitive_items(self, model):
        """Return a sorted list of all referenced items and items that are in
        the block's dependencies of the specified model."""
        items = " ".join(self.ref_items)
        if not items:
            return []

        (deps, _) = tools.execute("undertaker -j interesting -m %s %s"
                                  % (model.path, items))
        items_set = set()
        for dep in deps:
            items_set.update(tools.get_kconfig_items(dep))

        # filter Undertaker internal choice items (e.g., 'CONFIG_CHOICE_42',
        # 'CONFIG_CHOICE_42_MODULE', 'CONFIG_CHOICE_42_META')
        choice_regex = re.compile(r"CONFIG\_CHOICE\_\d+((?:_MODULE)|(?:_META)){,1}$")
        return sorted(itertools.ifilterfalse(choice_regex.match, items_set))

    @staticmethod
    def sort(blocks):
        """Sort blocks in ascending order with the block id as primary key."""
        # the second key is needed to have 'B00' before 'B0'
        return sorted(blocks, key=lambda x: (int(x.bid[1:]), -len(x.bid)))

    @staticmethod
    def parse_blocks(path):
        """Parse C source file and return a dictionary of
        blocks {block id:  block}."""
        blocks = {}
        try:
            (output, _) = tools.execute("undertaker -j blockrange %s" % path,
                                        failok=False)
        except tools.CommandFailed:
            return blocks
        for out in output:
            block = Block(path)
            split = out.split(":")
            block.bid = split[1]
            block.range = (int(split[2]), int(split[3]))
            block.new_range = block.range
            if block.range[0] != 0:
                (precond, _) = tools.execute("undertaker -j blockpc %s:%i:1" %
                                             (path, block.range[0]+1))
                block.precondition = precond
                for pre in precond:
                    block.ref_items.update(tools.get_kconfig_items(pre))
            # Add the file variable to the list of referenced items in order to
            #  make it visible to block.get_transitive_items()
            block.ref_items.add("FILE_" + kbuild.normalize_filename(block.srcfile))
            blocks[block.bid] = block
        return blocks

    @staticmethod
    def update_block_ranges(blocks, threshold, value):
        """Update ranges of each block in the @blocks list above threshold with
        @value and return them."""
        for block in blocks:
            block.update_range(threshold, value)
        return blocks

    @staticmethod
    def matchrange(block_a, block_b):
        """Return true if both blocks cover the same lines."""
        if block_a.range[0] == block_b.range[0] and \
                block_a.range[1] == block_b.range[1]:
            return True
        return False

    @staticmethod
    def parse_patchfile(patchfile, block_dict):
        """Parse the patchfile and update corresponding block ranges."""
        # https://pypi.python.org/pypi/whatthepatch/0.0.2
        diffs = None
        with open(patchfile) as stream:
            diffs = whatthepatch.parse_patch(stream.read())
        for diff in diffs:
            curr_file = diff.header.old_path
            # In some cases, whatthepatch will set the path to "a/path/to/file"
            # instead of "path/to/file", so we strip "a/" away to match with
            # the dictionary key in block_dict
            if curr_file.startswith("a/"):
                curr_file = curr_file[2:]
            # change format: [line before patch, line after patch, text]
            for change in diff.changes:
                # line removed
                if change[0] and not change[1]:
                    curr_line = int(change[0])
                    blocks = block_dict.get(curr_file, [])
                    blocks = Block.update_block_ranges(blocks, curr_line, -1)
                    block_dict[curr_file] = blocks
                # line added
                elif not change[0] and change[1]:
                    curr_line = int(change[1])
                    blocks = block_dict.get(curr_file, [])
                    blocks = Block.update_block_ranges(blocks, curr_line, 1)
                    block_dict[curr_file] = blocks

        # Set ranges to updated ranges
        for curr_file in block_dict:
            for block in block_dict[curr_file]:
                block.range = block.new_range
        return block_dict

    @staticmethod
    def get_block_id(report):
        """Return block ID of undertaker defect report."""
        match = re.match(r".+\.(B[0-9]+)\..+", report)
        if not match:
            raise ValueError("Could not get id of '%s'" % report)
        return match.groups()[0]

    @staticmethod
    def get_block_defect(report):
        """Return defect string of undertaker defect report."""
        match = re.match(r".+\.B[0-9]+\.(.+)", report)
        if not match:
            raise ValueError("Could not get defect of '%s'" % report)
        return match.groups()[0]

    @staticmethod
    def get_block_file(report):
        """Return the source file of undertaker defect report."""
        match = re.match(r"(.+)\.B[0-9]+\..+", report)
        if not match:
            raise ValueError("Could not get file of '%s'" % report)
        return match.groups()[0]
