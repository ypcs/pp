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
import stat
import errno
import shutil
import itertools

from .utils import BaseDirException, MyStat, get_package_info
from .aptfile import AptFsFile
from .download import download, DownloadError

fuse.fuse_python_api = (0, 2)
fuse.feature_assert('stateful_files', 'has_destroy')

class AptFs(fuse.Fuse):
    def __init__(self, *args, **kwargs):
        fuse.Fuse.__init__(self, *args, **kwargs)

        self.source_packages = {}
        self.binary_packages = {}

        self.max_unpacked_packages = 3
        self.secure = False
        self.temp_dir = None
        self.show_binary_symlinks = True

        self.window = []

    def main(self, *args, **kwargs):
        fuse.Fuse.main(self, *args, **kwargs)

    def fsinit(self):
        for x, y in get_package_info():
            self.source_packages[x] = None

            if self.show_binary_symlinks:
                for z in y:
                    self.binary_packages[z] = x

    def fsdestroy(self):
        for x in self.window:
            path = os.path.dirname(self.source_packages[x])
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
            try:
                target = download(pkg, self.temp_dir, self.secure)
            except DownloadError, e:
                shutil.rmtree(e.basedir)
                raise
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
            st = MyStat()
            st.st_mode = stat.S_IFDIR | 0755

            pkg = dir[0]
            if pkg == '':
                st.st_nlink = 2 + len(self.source_packages)
            else:
                st.st_nlink = 3

                if pkg not in self.source_packages and \
                    pkg not in self.binary_packages:
                    return -errno.ENOENT

                if pkg in self.binary_packages:
                    st.st_mode = stat.S_IFLNK | 0777

            return st

        try:
            return os.lstat(self.rewrite_path(path))
        except KeyError:
            return -errno.ENOENT

    def open(self, path, flags):
        return AptFsFile(self.rewrite_path(path), flags)

    def read(self, path, length, offset, fileobj):
        return fileobj.read(length, offset)

    def readlink(self, path):
        try:
            dir = path.split('/')[1:]
            if len(dir) == 1:
                pkg = dir[0]
                if not self.show_binary_symlinks or pkg == '':
                    return -errno.EACCES
                return self.binary_packages[pkg]

            return os.readlink(self.rewrite_path(path))
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def readdir(self, path, offset):
        try:
            for x in os.listdir(self.rewrite_path(path)):
                yield fuse.Direntry(x)

        except BaseDirException:
            yield fuse.Direntry('.')
            yield fuse.Direntry('..')

            if self.show_binary_symlinks:
                entries = itertools.chain(self.source_packages, self.binary_packages)
            else:
                entries = self.source_packages

            for x in sorted(entries):
                yield fuse.Direntry(x)

    def unlink(self, path):
        try:
            os.unlink(self.rewrite_path(path))
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def rmdir(self, path):
        try:
            os.rmdir(self.rewrite_path(path))
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def symlink(self, path, path1):
        try:
            os.symlink(path, self.rewrite_path(path1))
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def rename(self, path, path1):
        try:
            os.rename(self.rewrite_path(path), self.rewrite_path(path1))
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def link(self, path, path1):
        try:
            os.link(self.rewrite_path(path), self.rewrite_path(path1))
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def chmod(self, path, mode):
        try:
            os.chmod(self.rewrite_path(path), mode)
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def chown(self, path, user, group):
        try:
            os.chown(self.rewrite_path(path), user, group)
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def truncate(self, path, len):
        try:
            f = open(self.rewrite_path(path), "a")
            f.truncate(len)
            f.close()
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def mknod(self, path, mode, dev):
        try:
            os.mknod(self.rewrite_path(path), mode, dev)
        except KeyError:
            return -errno.EACCES

    def mkdir(self, path, mode):
        try:
            os.mkdir(self.rewrite_path(path), mode)
        except KeyError:
            return -errno.EACCES

    def utime(self, path, times):
        try:
            os.utime(self.rewrite_path(path), times)
        except (BaseDirException, KeyError):
            return -errno.EACCES

    def access(self, path, mode):
        try:
            if not os.access(self.rewrite_path(path), mode):
                return -errno.EACCES
        except BaseDirException:
            return 0

    def create(self, path, flags, *mode):
        try:
            return AptFsFile(self.rewrite_path(path), flags, *mode)
        except KeyError:
            return -errno.EACCES

    def flush(self, path, aptfile):
        try:
            self.rewrite_path(path)
            return aptfile.flush()
        except BaseDirException:
            return -errno.EACCES

    def write(self, path, buf, offset, aptfile):
        try:
            self.rewrite_path(path)
            return aptfile.write(buf, offset)
        except BaseDirException:
            return -errno.EACCES

    def release(self, path, flags, aptfile):
        try:
            self.rewrite_path(path)
            return aptfile.release(flags)
        except BaseDirException:
            return -errno.EACCES
