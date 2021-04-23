# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .exceptions import UnknownReferenceException

# Some references are not found in the dump file
MAGIC_REFERENCES = ("sound",)


class ImportSet:
    def __init__(self, raw_data, data_definition):
        self._data = raw_data
        self._data_definition = data_definition

    def check_references(self):
        unknown_references = set()
        referenced_resources = self._find_references()

        for tab, content in self._data.items():
            if not content:
                continue

            references = self._data_definition.get(tab, {}).get("references", [])
            for reference in references:
                headers = content[0]
                position = headers.index(reference)
                for row in content[1:]:
                    if position >= len(row):
                        # empty cel at the end of the row
                        continue
                    lookedup_reference = row[position]
                    if not lookedup_reference:
                        # Empty cel
                        continue
                    if lookedup_reference in MAGIC_REFERENCES:
                        continue
                    if lookedup_reference not in referenced_resources:
                        unknown_references.add(lookedup_reference)

        if unknown_references:
            raise UnknownReferenceException(list(unknown_references))

    def _find_references(self):
        references = {}

        for tab, content in self._data.items():
            if not content:
                continue

            headers = content[0]
            try:
                reference_column = headers.index("ref")
            except ValueError:
                continue

            for row in content[1:]:
                reference = row[reference_column]
                resource = zip(headers, row)
                references[reference] = resource

        return references
