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
import commands
import tempfile

class DownloadError(Exception):
    def __init__(self, output, basedir):
        self.basedir = basedir

        super(DownloadError, self).__init__(self, output)

def download(srcpkg, tempdir, secure=False):
    """
    Download and the specified source package and returns the base directory
    of the package, ie. just below 'download/'.

    Other apt-related information, including the diff.gz and original tarball
    are deleted.
    """

    base_path = None

    basedir = tempfile.mkdtemp('_%s' % srcpkg, 'aptfs_', tempdir)

    if secure:
        cmds = (
            'cd "%s"' % basedir,
            'apt-get source "%s"' % srcpkg,
        )
    else:
        cmds = (
            'cd "%s"' % basedir,
            'dget --quiet --download-only --allow-unauthenticated $(apt-get source ' + \
                '--print-uris "%s" | sed -n "s/\'\(http[^\']*.dsc\).*/\\1/p")' % srcpkg,

            # Break the signature such that dpkg-source does not attempt to verify it.
            'awk -v X=0 \'/^[ ]*$/ { X=1 } { if (X) print }\' *.dsc > src.dsc',
            'dpkg-source -x src.dsc unpacked',
        )
    status, output = commands.getstatusoutput(' && '.join(cmds))

    if status != 0:
        raise DownloadError(output, basedir)

    for x in os.listdir(basedir):
        path = os.path.join(basedir, x)

        # Delete everything except unpacked source tree
        if os.path.isdir(path):
            base_path = path
        else:
            os.unlink(path)

    if base_path is None:
        # No source directory found
        raise DownloadError(output, basedir)

    return base_path
