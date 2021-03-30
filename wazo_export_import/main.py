# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

from .dump import WazoGenerateDump


def dump(argv=sys.argv[1:]):
    app = WazoGenerateDump()
    return app.run(argv)
