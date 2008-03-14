# -*- coding: utf-8 -*-

# aptfs -- FUSE filesystem for APT source repositories
# Copyright (C) 2008 Chris Lamb <chris@chris-lamb.co.uk>
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

import os
import fuse
import popen2

def flag2mode(flags):
    md = {
        os.O_RDONLY : 'r',
        os.O_WRONLY : 'w',
        os.O_RDWR : 'w+'
    }
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)
    return m

class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

def package_info():

    stdout, stdin = popen2.popen2('grep-dctrl --invert-match --no-field-names --show-field=Package,Binary /var/lib/apt/lists/*_Sources')

    for line in stdout:
        source_package = line.strip()
        binary_packages = stdout.next().strip().split(', ')
        stdout.next() # Blank line

        try:
            binary_packages.remove(source_package)
        except ValueError:
            pass

        yield source_package, binary_packages

    stdin.close()
    stdout.close()
