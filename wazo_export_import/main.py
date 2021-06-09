# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import sys

from .dump import WazoGenerateDump
from .import_ import WazoImportDump

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s (%(levelname)s) (%(name)s): %(message)s",
)


def dump(argv=None):
    argv = argv or sys.argv[1:]
    app = WazoGenerateDump()
    return app.run(argv)


def import_(argv=None):
    argv = argv or sys.argv[1:]
    app = WazoImportDump()
    return app.run(argv)
