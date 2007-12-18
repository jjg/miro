#!/bin/sh

# Miro - an RSS based video player application
# Copyright (C) 2005-2007 Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

PYTHON=`which python`
PYTHON_VERSION=`python -c 'import sys; info=sys.version_info; print "%s.%s" % (info[0], info[1])'`
PREFIX=/usr
export MIRO_SHARE_ROOT=dist/$PREFIX/share/
export MIRO_RESOURCE_ROOT=dist/$PREFIX/share/miro/resources/

PYTHON_PATH=dist/$PREFIX/lib/python$PYTHON_VERSION/site-packages/

if [ -d dist/$PREFIX/lib64/ ]
then
  # adding on to the existing path with lib64 trumping lib
  PYTHON_PATH=dist/$PREFIX/lib64/python$PYTHON_VERSION/site-packages/:$PYTHON_PATH
fi

# NOTE: The first part of this LD_LIBRARY_PATH _must_ match what setup.py
# picks out and puts in dist/usr/bin/miro .  If you're having problems
# running miro with ./run.sh, then make sure you've got the LD_LIBRARY_PATH
# portion matching.
# This line probably doesn't need to be here since we call "miro" which sets
# the LD_LIBRARY_PATH correctly anyhow.
# export LD_LIBRARY_PATH=/usr/lib/firefox${LD_LIBRARY_PATH:+:}${LD_LIBRARY_PATH}

$PYTHON setup.py install --root=./dist --prefix=$PREFIX && PATH=dist/$PREFIX/bin:$PATH PYTHONPATH=$PYTHON_PATH dist/$PREFIX/bin/miro "$@"
# $PYTHON setup.py install --root=./dist --prefix=$PREFIX
