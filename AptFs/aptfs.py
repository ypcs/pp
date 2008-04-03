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
import time
import shutil

from fuse import Fuse
from errno import *
from stat import *
from itertools import chain

from AptFs import util
from AptFs.aptfile import AptFsFile
from AptFs.download import download, DownloadError

fuse.fuse_python_api = (0, 2)
fuse.feature_assert('stateful_files', 'has_destroy')

class BaseDirException(Exception): pass

class AptFs(Fuse):
    def __init__(self, *args, **kwargs):
        Fuse.__init__(self, *args, **kwargs)

        self.source_packages = {}
        self.binary_packages = {}
        for source_package, binary_packages in util.package_info():
            self.source_packages[source_package] = None

            for binary_package in binary_packages:
                self.binary_packages[binary_package] = source_package

        self.max_unpacked_packages = 3
        self.secure = False
        self.temp_dir = None

        self.window = []

    def main(self, *a, **kwargs):
        Fuse.main(self, *a, **kwargs)

        for srcpkg in self.window:
            path = os.path.dirname(self.source_packages[srcpkg])
            shutil.rmtree(path)

    ##

    def rewrite_path(self, path):
        dir = path.split('/')[1:]

        def parse_path():
            pkg = dir[0]
            if pkg == '':
                raise BaseDirException

            try:
                return pkg, self.source_packages[pkg]
            except KeyError:
                pkg = self.binary_packages[pkg]
                return pkg, self.source_packages[pkg]

        pkg, target = parse_path()
        if target is None:
            target = download(pkg, self.temp_dir, self.secure)
            self.source_packages[pkg] = target
            self.window.insert(0, pkg)

            while len(self.window) > self.max_unpacked_packages:
                srcpkg = self.window.pop()
                del_path = self.source_packages[srcpkg]
                shutil.rmtree(os.path.dirname(del_path))
                self.source_packages[srcpkg] = None

        return target + '/' + '/'.join(dir[1:])

    def getattr(self, path):
        dir = path.split('/')[1:]
        if len(dir) == 1:
            st = util.MyStat()
            st.st_mode = S_IFDIR | 0755

            pkg = dir[0]
            if pkg == '':
                st.st_nlink = 2 + len(self.source_packages)
            else:
                st.st_nlink = 3

                if pkg not in self.source_packages and \
                    pkg not in self.binary_packages:
                    return -EACCES

                if pkg in self.binary_packages:
                    st.st_mode = S_IFLNK | 0777

            return st

        try:
            return os.lstat(self.rewrite_path(path))
        except KeyError:
            return -ENOENT

    def open(self, path, flags):
        return AptFsFile(self.rewrite_path(path), flags)

    def read(self, path, length, offset, fileobj):
        return fileobj.read(length, offset)

    def readlink(self, path):
        try:
            dir = path.split('/')[1:]
            if len(dir) == 1:
                pkg = dir[0]
                if pkg == '':
                    return -EACCES
                return self.binary_packages[pkg]

            return os.readlink(self.rewrite_path(path))
        except (BaseDirException, KeyError):
            return -EACCES

    def readdir(self, path, offset):
        try:
            for e in os.listdir(self.rewrite_path(path)):
                yield fuse.Direntry(e)

        except BaseDirException:
            yield fuse.Direntry('.')
            yield fuse.Direntry('..')

            all_packages = chain(self.source_packages, self.binary_packages)
            for e in sorted(all_packages):
                yield fuse.Direntry(e)

    def unlink(self, path):
        try:
            os.unlink(self.rewrite_path(path))
        except (BaseDirException, KeyError):
            return -EACCES

    def rmdir(self, path):
        try:
            os.rmdir(self.rewrite_path(path))
        except (BaseDirException, KeyError):
            return -EACCES

    def symlink(self, path, path1):
        try:
            os.symlink(path, self.rewrite_path(path1))
        except (BaseDirException, KeyError):
            return -EACCES

    def rename(self, path, path1):
        try:
            os.rename(self.rewrite_path(path), self.rewrite_path(path1))
        except (BaseDirException, KeyError):
            return -EACCES

    def link(self, path, path1):
        try:
            os.link(self.rewrite_path(path), self.rewrite_path(path1))
        except (BaseDirException, KeyError):
            return -EACCES

    def chmod(self, path, mode):
        try:
            os.chmod(self.rewrite_path(path), mode)
        except (BaseDirException, KeyError):
            return -EACCES

    def chown(self, path, user, group):
        try:
            os.chown(self.rewrite_path(path), user, group)
        except (BaseDirException, KeyError):
            return -EACCES

    def truncate(self, path, len):
        try:
            f = open(self.rewrite_path(path), "a")
            f.truncate(len)
            f.close()
        except (BaseDirException, KeyError):
            return -EACCES

    def mknod(self, path, mode, dev):
        try:
            os.mknod(self.rewrite_path(path), mode, dev)
        except KeyError:
            return -EACCES

    def mkdir(self, path, mode):
        try:
            os.mkdir(self.rewrite_path(path), mode)
        except KeyError:
            return -EACCES

    def utime(self, path, times):
        try:
            os.utime(self.rewrite_path(path), times)
        except (BaseDirException, KeyError):
            return -EACCES

    def access(self, path, mode):
        try:
            if not os.access(self.rewrite_path(path), mode):
                return -EACCES
        except BaseDirException:
            return 0

    def create(self, path, flags, *mode):
        try:
            return AptFsFile(self.rewrite_path(path), flags, *mode)
        except KeyError:
            return -EACCES

    def flush(self, path, aptfile):
        try:
            self.rewrite_path(path)
            return aptfile.flush()
        except BaseDirException:
            return -EACCES

    def write(self, path, buf, offset, aptfile):
        try:
            self.rewrite_path(path)
            return aptfile.write(buf, offset)
        except BaseDirException:
            return -EACCES

    def release(self, path, flags, aptfile):
        try:
            self.rewrite_path(path)
            return aptfile.release(flags)
        except BaseDirException:
            return -EACCES
