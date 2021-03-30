# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from cliff import app, commandmanager


class WazoGenerateDump(app.App):
    def __init__(self):
        super().__init__(
            description='A dump file builder for Wazo',
            command_manager=commandmanager.CommandManager(
                'wazo_export_import.dump_commands'
            ),
            version='0.0.1',
        )
