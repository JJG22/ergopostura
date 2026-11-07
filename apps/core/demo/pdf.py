"""PDF de texto minimo, sin dependencias, para los contratos de demostracion y las pruebas.

Usa la fuente Helvetica incluida en todo lector de PDF, con la codificacion WinAnsi, que
cubre las tildes y la ñ del español.
"""

PAGE_WIDTH, PAGE_HEIGHT = 612, 792  # carta, en puntos
MARGIN = 64
LINE_HEIGHT = 15
FONT_SIZE = 10.5
CHARS_PER_LINE = 92
LINES_PER_PAGE = (PAGE_HEIGHT - 2 * MARGIN) // LINE_HEIGHT


def _wrap(paragraph: str) -> list[str]:
    words, lines, current = paragraph.split(), [], ""
    for word in words:
        if current and len(current) + 1 + len(word) > CHARS_PER_LINE:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    lines.append(current)
    return lines


def _escape(text: str) -> bytes:
    raw = text.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def text_pdf(title: str, paragraphs: list[str]) -> bytes:
    lines = [title.upper(), ""]
    for paragraph in paragraphs:
        lines += _wrap(paragraph) + [""]
    pages = [lines[start:start + LINES_PER_PAGE] for start in range(0, len(lines), LINES_PER_PAGE)]

    objects: list[bytes] = []
    page_ids = []
    font_id = 3
    next_id = 4
    contents = []
    for page_lines in pages:
        stream = [b"BT", f"/F1 {FONT_SIZE} Tf {LINE_HEIGHT} TL".encode(), f"{MARGIN} {PAGE_HEIGHT - MARGIN} Td".encode()]
        for line in page_lines:
            stream.append(b"(" + _escape(line) + b") Tj T*")
        stream.append(b"ET")
        contents.append(b"\n".join(stream))
        page_ids.append(next_id)
        next_id += 2

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for page_id, content in zip(page_ids, contents):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {page_id + 1} 0 R >>".encode()
        )
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode()
    output += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(output)
