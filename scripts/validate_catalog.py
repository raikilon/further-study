#!/usr/bin/env python3
"""Validate the static program catalog before publishing it."""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_CREDENTIALS = {"CAS", "MAS"}
ALLOWED_LANGUAGES = {"de", "fr", "it", "en"}
ALLOWED_FORMATS = {"in-person", "hybrid", "online", "varies", None}
ALLOWED_SUBJECTS = {
    "ai-data",
    "business-leadership",
    "health-life-sciences",
    "arts-society",
    "sustainability",
    "other",
}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED_TEXT = ("id", "title", "provider", "city", "summary", "sourceUrl", "verifiedAt")


def validate(path):
    try:
        catalog = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return ["Could not read catalog: {}".format(error)], 0

    if not isinstance(catalog, list) or not catalog:
        return ["Catalog must be a non-empty JSON array."], 0

    errors = []
    ids = set()
    sources = set()
    for index, program in enumerate(catalog, start=1):
        if not isinstance(program, dict):
            errors.append("Entry {} must be an object.".format(index))
            continue

        label = "Entry {} ({})".format(index, program.get("id", "no id"))
        for field in REQUIRED_TEXT:
            value = program.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append("{}: '{}' must be a non-empty string.".format(label, field))

        if not isinstance(program.get("credential"), str) or program.get("credential") not in ALLOWED_CREDENTIALS:
            errors.append("{}: credential must be CAS or MAS.".format(label))
        if not isinstance(program.get("subject"), str) or program.get("subject") not in ALLOWED_SUBJECTS:
            errors.append("{}: unsupported subject.".format(label))
        languages = program.get("languages")
        if not isinstance(languages, list) or any(not isinstance(language, str) or language not in ALLOWED_LANGUAGES for language in languages):
            errors.append("{}: languages must be an array containing only de/fr/it/en.".format(label))
        program_format = program.get("format")
        if (program_format is not None and not isinstance(program_format, str)) or program_format not in ALLOWED_FORMATS:
            errors.append("{}: unsupported study format.".format(label))
        if not isinstance(program.get("tags"), list):
            errors.append("{}: tags must be an array.".format(label))
        if program.get("ects") is not None and (not isinstance(program["ects"], (int, float)) or program["ects"] <= 0):
            errors.append("{}: ects must be a positive number or null.".format(label))
        if program.get("priceCHF") is not None and (not isinstance(program["priceCHF"], (int, float)) or program["priceCHF"] < 0):
            errors.append("{}: priceCHF must be zero or a positive number, or null.".format(label))
        if program.get("nextStart") is not None and not DATE_PATTERN.match(str(program["nextStart"])):
            errors.append("{}: nextStart must use YYYY-MM-DD or be null.".format(label))
        if program.get("verifiedAt") and not DATE_PATTERN.match(str(program["verifiedAt"])):
            errors.append("{}: verifiedAt must use YYYY-MM-DD.".format(label))

        source = program.get("sourceUrl", "")
        try:
            parsed = urlparse(source) if isinstance(source, str) else None
            if not parsed or parsed.scheme != "https" or not parsed.netloc:
                errors.append("{}: sourceUrl must be an absolute HTTPS URL.".format(label))
        except (TypeError, ValueError):
            errors.append("{}: sourceUrl must be a valid URL.".format(label))

        program_id = program.get("id")
        if isinstance(program_id, str) and program_id in ids:
            errors.append("{}: duplicate id.".format(label))
        if isinstance(program_id, str) and program_id:
            ids.add(program_id)
        if isinstance(source, str) and source in sources:
            errors.append("{}: duplicate sourceUrl.".format(label))
        if isinstance(source, str) and source:
            sources.add(source)

    return errors, len(catalog)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "public/data/programs.json"
    errors, count = validate(path)
    if errors:
        print("Catalog validation failed:")
        for error in errors:
            print("- " + error)
        return 1
    print("Catalog valid: {} program entries.".format(count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
