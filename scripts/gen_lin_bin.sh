#!/bin/sh -e

echo "__version__ = '$(cat VERSION)'" > cli/version.py
pip3 install .
pyinstaller cli/mason.py --onefile \
  --hidden-import='pkg_resources.py2_warn' \
  --add-data "$(pip3 show pyaxmlparser | grep Location | cut -c11-)/pyaxmlparser/resources/public.xml:pyaxmlparser/resources" \
  --add-data VERSION:.

./dist/mason version
