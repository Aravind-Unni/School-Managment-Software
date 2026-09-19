"""The languages this platform publishes records and UI in.

One definition, because more than one module needs it: M02 stores a school's
default language and each pupil's preferred language, and the frontend renders
both. Two copies would let them drift, and a schema generator would emit two
differently-named enums for what is one set of values.

Adding a language is a contract revision, not an edit here: every frozen enum
that lists these values would have to move with it.
"""

from __future__ import annotations

#: (value, label) pairs, in the order a chooser should present them.
LANGUAGE_CHOICES: tuple[tuple[str, str], ...] = (("en", "English"), ("ml", "Malayalam"))

#: Just the stored values, for schema and validation use.
LANGUAGE_VALUES: tuple[str, ...] = tuple(value for value, _ in LANGUAGE_CHOICES)
