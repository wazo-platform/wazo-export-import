# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

from .dump import WazoGenerateDump
from .import_ import WazoImportDump


def dump(argv=None):
    argv = argv or sys.argv[1:]
    app = WazoGenerateDump()
    return app.run(argv)


def import_(argv=None):
    argv = argv or sys.argv[1:]
    app = WazoImportDump()
    return app.run(argv)
