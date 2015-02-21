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
import errno
import fcntl

from .utils import flag_to_mode

class AptFsFile(object):
    def __init__(self, path, flags, *mode):
        self.file = os.fdopen(os.open(path, flags, *mode), flag_to_mode(flags))
        self.fd = self.file.fileno()

    def read(self, length, offset):
        self.file.seek(offset)
        return self.file.read(length)

    def write(self, buf, offset):
        self.file.seek(offset)
        self.file.write(buf)
        return len(buf)

    def release(self, flags):
        self.file.close()

    def _fflush(self):
        if 'w' in self.file.mode or 'a' in self.file.mode:
            self.file.flush()

    def fsync(self, isfsyncfile):
        self._fflush()
        if isfsyncfile and hasattr(os, 'fdatasync'):
            os.fdatasync(self.fd)
        else:
            os.fsync(self.fd)

    def flush(self):
        self._fflush()
        return os.close(os.dup(self.fd))

    def fgetattr(self):
        return os.fstat(self.fd)

    def ftruncate(self, len):
        self.file.truncate(len)

    def lock(self, cmd, owner, **kwargs):
        op = {
            fcntl.F_UNLCK : fcntl.LOCK_UN,
            fcntl.F_RDLCK : fcntl.LOCK_SH,
            fcntl.F_WRLCK : fcntl.LOCK_EX,
        }[kwargs['l_type']]

        if cmd == fcntl.F_GETLK:
            return -errno.EOPNOTSUPP
        elif cmd == fcntl.F_SETLK:
            if op != fcntl.LOCK_UN:
                op |= fcntl.LOCK_NB
        elif cmd == fcntl.F_SETLKW:
            pass
        else:
            return -errno.EINVAL

        fcntl.lockf(self.fd, op, kwargs['l_start'], kwargs['l_len'])
