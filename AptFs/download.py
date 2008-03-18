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

import tempfile
import commands
import os

class DownloadError(Exception): pass

def download(srcpkg, tempdir=None):
    '''
    Download and the specified source package and returns the base directory
    of the package, ie. just below 'download/'.

    Other apt-related information, including the diff.gz and original tarball
    are deleted.
    '''
    base_path = None

    dir = tempfile.mkdtemp('_%s' % srcpkg, 'aptfs_', tempdir)

    cmds = (
        'cd "%s"' % dir,
        'dget --quiet --download-only --allow-unauthenticated $(apt-get source --print-uris "%s" | sed -n "s/\'\(http[^\']*.dsc\).*/\\1/p")' % srcpkg,
        'sed -i \'1,3d\' *.dsc',
        'dpkg-source -x *.dsc unpacked',
    )
    status, output = commands.getstatusoutput(' && '.join(cmds))

    if status != 0:
        raise DownloadError

    for fname in os.listdir(dir):
        path = os.path.join(dir, fname)

        # Delete everything except unpacked source tree
        if os.path.isdir(path):
            base_path = path
        else:
            os.unlink(path)

    if base_path is None:
        # No source directory found
        raise DownloadError

    return base_path
