# -*- coding: utf-8 -*-

# aptfs — FUSE filesystem for APT source repositories
# Copyright © 2008—2017 Chris Lamb <lamby@debian.org>
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
import subprocess


class BaseDirException(Exception):
    pass


def get_package_info():
    filenames = subprocess.check_output((
        'apt-get',
        'indextargets',
        '--format', '$(FILENAME)',
        'Created-By: Sources',
    )).splitlines()

    apt_helper = subprocess.Popen((
        '/usr/lib/apt/apt-helper',
        'cat-file',
    ) + tuple(filenames), stdout=subprocess.PIPE)

    stdout = subprocess.check_output((
        'grep-dctrl',
        '-FSource:Package',
        '--regex', '.',
        '--no-field-names',
        '--show-field=Package,Binary',
    ), stdin=apt_helper.stdout)

    apt_helper.wait()

    for x in stdout.split('\n\n'):
        if not x:
            continue
        src, ys = x.split('\n', 1)
        yield src, {y for y in ys.split(', ') if y != src}


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
