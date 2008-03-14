from distutils.core import setup

setup(
    name = 'aptfs',
    version = '0.1',
    author = 'Chris Lamb',
    author_email = 'chris@chris-lamb.co.uk',
    packages = ['AptFs'],
    scripts = ['mount.aptfs'],
)
