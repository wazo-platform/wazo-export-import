# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import csv
import sys

from cliff import command

from .helpers.ods import DumpFile
from .helpers.constants import RESOURCE_FIELDS


class Import(command.Command):
    def get_parser(self, *args, **kwargs):
        parser = super().get_parser(*args, **kwargs)
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        tenant_selector = parser.add_mutually_exclusive_group(required=True)
        tenant_selector.add_argument("--tenant", dest="tenant_uuid")
        tenant_selector.add_argument(
            "--new-tenant", dest="new_tenant", action="store_const", const=True
        )
        parser.add_argument(
            "filename",
            help="dump filename to read from",
        )
        return parser

    def take_action(self, parsed_args):
        pass


class ListResources(command.Command):
    def take_action(self, parsed_args):
        return " ".join(RESOURCE_FIELDS.keys())


class ListFields(command.Command):
    def get_parser(self, *args, **kwargs):
        parser = super().get_parser(*args, **kwargs)
        relation = parser.add_mutually_exclusive_group(required=True)
        for resource in RESOURCE_FIELDS.keys():
            relation.add_argument(
                "--{}".format(resource),
                dest="resource",
                action="store_const",
                const=resource,
            )
        return parser

    def take_action(self, parsed_args):
        return " ".join(RESOURCE_FIELDS[parsed_args.resource]["fields"].keys())


class Add(command.Command):
    def get_parser(self, *args, **kwargs):
        parser = super().get_parser(*args, **kwargs)
        relation = parser.add_mutually_exclusive_group(required=True)
        for resource in RESOURCE_FIELDS.keys():
            relation.add_argument(
                "--{}".format(resource),
                dest="resource",
                action="store_const",
                const=resource,
            )
        parser.add_argument(
            "filename",
            help="dump filename to the resources to",
        )
        return parser

    def take_action(self, parsed_args):
        reader = csv.DictReader(sys.stdin)
        first_row = True
        with DumpFile(parsed_args.filename) as dump_file:
            for row in reader:
                if first_row:
                    self._validate_columns(parsed_args.resource, row)
                    first_row = False
                self._add_or_update_resource(dump_file, parsed_args.resource, row)

    def _validate_columns(self, resource, row):
        known_columns = set(RESOURCE_FIELDS[resource]["fields"].keys())
        user_supplied_columns = set(row.keys())

        unknown_columns = user_supplied_columns - known_columns
        if unknown_columns:
            raise Exception("unknown columns {}".format(",".join(unknown_columns)))

    def _add_or_update_resource(self, dump_file, resource, row):
        try:
            index = self._find_matching_resource(dump_file, resource, row)
            dump_file.update_row(resource, index, row)
        except LookupError:
            dump_file.add_row(resource, row)

    def _find_matching_resource(self, dump_file, resource, row):
        selections = RESOURCE_FIELDS[resource]["unique"]
        for unique_columns in selections:
            row_has_all_columns = set(row.keys()).issuperset(set(unique_columns))
            if row_has_all_columns:
                pairs = [(key, row[key]) for key in unique_columns]
                try:
                    return dump_file.find_matching_row(resource, pairs)
                except LookupError:
                    continue
        raise LookupError("No resource matching")


class New(command.Command):
    def get_parser(self, *args, **kwargs):
        parser = super().get_parser(*args, **kwargs)
        parser.add_argument(
            "filename",
            help="dump filename to the resources to",
        )
        return parser

    def take_action(self, parsed_args):
        with DumpFile(parsed_args.filename):
            # Dump creation side effect
            pass
