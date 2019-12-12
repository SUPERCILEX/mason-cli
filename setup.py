from setuptools import setup, find_packages

import os


root = os.path.dirname(os.path.realpath(__file__))

# Read version
with open(os.path.join(root, "VERSION"), "r") as f:
    version = f.read().strip()

# Write version.py
with open(os.path.join(root, "masonlib/version.py"), "w") as f:
    f.write("__version__ = '{}'".format(version))


setup(
    name='mason-cli',
    version=version,
    zip_safe=False,
    packages=find_packages(),
    install_requires=[
        'click>=7.0',
        'click-log',
        'requests',
        'tqdm',
        'pyyaml',
        'six',
        'packaging',
        'pyaxmlparser>=0.3.22',
        'future',  # Needed for Python 2 compatibility
        'adb @ https://github.com/MasonAmerica/python-adb/tarball/master#egg=adb-1.3.0.8',
        'twisted>=19.10.0',
        'autobahn>=19.11.1',
        'service_identity',
        'pyopenssl>=19.1.0',
        'pyasn1>=0.4.7'
    ],
    entry_points={
        'console_scripts': [
            'mason = masonlib.mason:cli'
        ]
    },
    include_package_data=True,
)
