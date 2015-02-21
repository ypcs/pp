# -*- coding: utf-8 -*-

# aptfs — FUSE filesystem for APT source repositories
# Copyright © 2008—2015 Chris Lamb <lamby@debian.org>
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
import glob
import popen2

class BaseDirException(Exception):
    pass

def get_package_info():
    if not glob.glob('/var/lib/apt/lists/*_Sources'):
        raise StopIteration()

    # FIXME: Move to subprocess
    stdout, stdin = popen2.popen2('grep-dctrl -FSource:Package --regex . --no-field-names --show-field=Package,Binary /var/lib/apt/lists/*_Sources')

    for line in stdout:
        src = line.strip()
        binaries = set()

        while True:
            line = stdout.next()
            if line == '\n':
                break
            binaries.update(x for x in line.strip().split(', ') if x)

        binaries.discard(src)

        yield src, binaries

    stdin.close()
    stdout.close()

def flag_to_mode(flags):
    md = {
        os.O_RDWR: 'w+',
        os.O_RDONLY: 'r',
        os.O_WRONLY: 'w',
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
