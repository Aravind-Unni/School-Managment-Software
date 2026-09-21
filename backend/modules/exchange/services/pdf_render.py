"""A minimal, pure-Python PDF writer. No new dependency, no font bundle.

WHAT THIS DOES: produces a syntactically valid single-page PDF whose text is
carried as UTF-8 in an uncompressed content stream, with the same text repeated
in an XMP metadata stream and the document catalogue marked ``/Lang``. Malayalam
survives into the artifact bytes verbatim, which is what the report-card
acceptance asserts.

WHAT THIS DOES NOT DO, stated because the difference matters to a parent holding
the printout: it does not embed a font, and it does not shape Malayalam
conjuncts. Review-decisions item 10 requires an embedded Malayalam font bundle
and names approving it as a HUMAN GATE that has not happened. Until that bundle
is approved and added, a viewer without a Malayalam font will show tofu, and
this module must not claim otherwise. ``FONT_BUNDLE_PENDING`` is written into
every document's metadata so an artifact produced before the gate is
identifiable after it.

Also does not handle: multiple pages, images, encryption or compression.
"""

from __future__ import annotations

#: Recorded in each document's metadata until the font gate is passed.
FONT_BUNDLE_PENDING = "pending-human-approval"

#: PDF's own escaping rules for a literal string. Backslash first, or the
#: escapes inserted after it would be escaped again.
_LITERAL_ESCAPES = ((b"\\", b"\\\\"), (b"(", b"\\("), (b")", b"\\)"))


def escape_literal(text: str) -> bytes:
    """Return ``text`` as UTF-8 bytes safe inside a PDF literal string.

    UTF-8 rather than UTF-16BE hex on purpose: the bytes must remain greppable,
    so an acceptance test can prove the Malayalam text reached the artifact
    rather than trusting the writer.
    """
    body = text.encode("utf-8")
    for raw, replacement in _LITERAL_ESCAPES:
        body = body.replace(raw, replacement)
    return body


def _content_stream(lines: list[str]) -> bytes:
    """Return the page content stream drawing each line of text."""
    parts = [b"BT", b"/F1 12 Tf", b"14 TL", b"56 760 Td"]
    for line in lines:
        parts.append(b"(" + escape_literal(line) + b") Tj")
        parts.append(b"T*")
    parts.append(b"ET")
    return b"\n".join(parts)


def _xmp_metadata(title: str, lines: list[str], locale: str) -> bytes:
    """Return an XMP packet carrying the title, locale and every text line.

    The text appears twice in the document — once drawn, once as metadata — so
    that an extractor that cannot handle the unembedded font can still recover
    what the report said.
    """
    body = "\n".join(lines)
    return (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"   <dc:title>{title}</dc:title>\n"
        f"   <dc:language>{locale}</dc:language>\n"
        f"   <dc:description>{body}</dc:description>\n"
        f"   <dc:source>font-bundle:{FONT_BUNDLE_PENDING}</dc:source>\n"
        "  </rdf:Description>\n"
        " </rdf:RDF>\n"
        "</x:xmpmeta>\n"
        '<?xpacket end="w"?>'
    ).encode()


def render_pdf(*, title: str, lines: list[str], locale: str) -> bytes:
    """Return a one-page PDF carrying ``title`` and ``lines`` as UTF-8 text.

    Assumes the caller has already localised the strings; this function does no
    translation and no line wrapping. ``locale`` is written to the catalogue's
    ``/Lang`` so a reader knows which language to look for.

    Does not handle: text longer than one page. Extra lines run off the bottom
    rather than paginating, which is acceptable only because the fixture report
    card is short and is recorded as a limitation in the handoff.
    """
    content = _content_stream([title, *lines])
    metadata = _xmp_metadata(title, lines, locale)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R /Lang ("
        + escape_literal(locale)
        + b") /Metadata 6 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length "
        + str(len(content)).encode("ascii")
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
        b"<< /Type /Metadata /Subtype /XML /Length "
        + str(len(metadata)).encode("ascii")
        + b" >>\nstream\n"
        + metadata
        + b"\nendstream",
    ]
    return _assemble(objects)


def _assemble(objects: list[bytes]) -> bytes:
    """Return a complete PDF file from numbered object bodies.

    Builds the cross-reference table from the real byte offsets as it goes,
    because an xref with guessed offsets produces a file that opens in some
    readers and silently fails in others.
    """
    out = bytearray(b"%PDF-1.7\n%\xe0\xe1\xe2\xe3\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)
