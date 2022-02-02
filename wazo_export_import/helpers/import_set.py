# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from .exceptions import DuplicateReferenceException, UnknownReferenceException

logger = logging.getLogger(__name__)

# Some references are not found in the dump file
MAGIC_REFERENCES = ("sound",)


def convert_value(value):
    # Convert values from postgresql format to python values
    if value == "true":
        return True
    elif value == "false":
        return False
    else:
        return value


class ImportSet:
    def __init__(self, raw_data, data_definition):
        self._data = raw_data
        self._data_definition = data_definition
        self._resources = {}
        for resource_type in data_definition.keys():
            self._resources[resource_type] = []
        self._referenced_resources = {}

        self._build_resources()
        self._build_references()

    def _build_resources(self):
        logger.info("building all resources")
        for type_, content in self._data.items():
            if not content:
                continue

            headers = content[0]
            for row in content[1:]:
                resource = {k: convert_value(v) for k, v in zip(headers, row)}
                resource["type_"] = type_
                if type_ not in self._resources:
                    self._resources[type_] = []
                logger.debug("resource built : %s", resource)
                self._resources[type_].append(resource)
        logger.debug("resource building done")

    def _build_references(self):
        logger.info("building references")
        for resources in self._resources.values():
            if not resources:
                continue  # There's no resources for this type

            headers = list(resources[0].keys())
            if "ref" not in headers:
                continue  # The resources in this list have no "ref" column

            for resource in resources:
                reference = resource["ref"]
                if not reference:
                    continue
                logger.debug("reference built : %s", reference)
                if reference in self._referenced_resources:
                    raise DuplicateReferenceException(reference)

                self._referenced_resources[reference] = resource
        logger.debug("reference building done")

    def check_references(self):
        logger.info("checking references")
        unknown_references = set()

        for type_, resources in self._resources.items():
            if not resources:
                continue

            references = self._data_definition.get(type_, {}).get("references", [])
            for reference in references:
                for resource in resources:
                    lookedup_reference = resource.get(reference)
                    if not lookedup_reference:
                        continue
                    if lookedup_reference in MAGIC_REFERENCES:
                        continue
                    if lookedup_reference not in self._referenced_resources:
                        unknown_references.add(lookedup_reference)

        logger.debug("reference checking done")

        if unknown_references:
            raise UnknownReferenceException(list(unknown_references))

    def list(self, resource_type):
        return self._resources.get(resource_type, [])

    def get_resource(self, reference):
        return self._referenced_resources.get(reference)
