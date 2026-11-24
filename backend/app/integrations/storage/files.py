"""Upload validation and processing for every file a technician can attach.

Checks the real bytes, never the browser's MIME type or the file name:
- images (JPEG, PNG, WebP): decoded, pixel count limited, rotated upright from EXIF, then re-encoded WITHOUT metadata,
  so GPS location and camera details in phone photos never reach the server's storage or the AI;
- PDF: must parse, must not be encrypted, page limit, text extracted for search and display;
- Word (.docx): read as a ZIP with size limits (no zip bombs), text extracted from document.xml only, no macros or embedded files;
- plain text (.txt, .csv, .md, .log): must be valid UTF-8 text with no binary bytes.
Anything else is refused with UNSUPPORTED_MEDIA_TYPE.
"""
import io, re, zipfile
from dataclasses import dataclass, field
from PIL import Image, ImageOps, UnidentifiedImageError
from ...config import get_settings
from .local import InvalidUpload

IMAGE_FORMATS = {'JPEG': ('image/jpeg', 'jpg'), 'PNG': ('image/png', 'png'), 'WEBP': ('image/webp', 'webp')}
TEXT_TYPES = {'txt': 'text/plain', 'log': 'text/plain', 'md': 'text/markdown', 'csv': 'text/csv'}
DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
MAX_PIXELS = 40_000_000
MAX_PDF_PAGES = 60
MAX_TEXT_CHARS = 60_000          # kept for the AI and previews; longer documents are truncated and say so
MAX_DOCX_XML_BYTES = 25 * 1024 * 1024
SUPPORTED_HINT = 'Supported: JPG, PNG or WebP images, PDF, Word (.docx), and text files (.txt, .csv, .md).'


@dataclass
class Processed:
    kind: str            # 'image' | 'document'
    mime: str
    ext: str
    data: bytes          # what is stored (images are re-encoded without metadata)
    width: int | None = None
    height: int | None = None
    meta: dict = field(default_factory=dict)


def safe_name(name: str | None, fallback: str) -> str:
    """A display name only: never used as a path. Strips folders and control characters."""
    n = (name or '').replace('\\', '/').split('/')[-1]
    n = re.sub(r'[\x00-\x1f\x7f<>:"|?*]', '', n).strip(' .')
    return (n or fallback)[:120]


def _limit_bytes(kind: str) -> int:
    s = get_settings()
    return (s.max_document_size_mb if kind == 'document' else s.max_upload_size_mb) * 1024 * 1024


def process_image(data: bytes) -> Processed:
    s = get_settings()
    if len(data) > s.max_upload_size_mb * 1024 * 1024:
        raise InvalidUpload(f'Image is larger than {s.max_upload_size_mb} MB.', code='UPLOAD_TOO_LARGE', status=413)
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format; w, h = probe.size
            if w * h > MAX_PIXELS:
                raise InvalidUpload('Image resolution is too large. Please use a photo under 40 megapixels.', code='UPLOAD_TOO_LARGE', status=413)
            probe.verify()
        if fmt not in IMAGE_FORMATS:
            raise InvalidUpload('Only JPEG, PNG or WebP images are accepted.', code='UNSUPPORTED_MEDIA_TYPE', status=415)
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            im = ImageOps.exif_transpose(im)  # upright, as the phone showed it
            out = io.BytesIO()
            if fmt == 'JPEG':
                im.convert('RGB').save(out, 'JPEG', quality=90, optimize=True)  # no exif= argument: metadata dropped
            elif fmt == 'PNG':
                im.save(out, 'PNG', optimize=True)
            else:
                im.save(out, 'WEBP', quality=90)
            w, h = im.size
    except InvalidUpload:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise InvalidUpload('File is not a valid JPEG, PNG or WebP image.', code='UNSUPPORTED_MEDIA_TYPE', status=415)
    mime, ext = IMAGE_FORMATS[fmt]
    return Processed('image', mime, ext, out.getvalue(), w, h, {'metadata_removed': True})


def _clip(text: str) -> tuple[str, bool]:
    text = re.sub(r'[ \t]+', ' ', text).replace('\r', '')
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return (text[:MAX_TEXT_CHARS], len(text) > MAX_TEXT_CHARS)


def process_pdf(data: bytes, name: str) -> Processed:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
    try:
        r = PdfReader(io.BytesIO(data), strict=False)
        if r.is_encrypted:
            try:
                ok = r.decrypt('')
            except Exception:  # noqa: BLE001
                ok = 0
            if not ok:
                raise InvalidUpload('This PDF is password-protected. Remove the password and upload it again.', code='PDF_ENCRYPTED', status=415)
        pages = len(r.pages)
        if pages == 0:
            raise InvalidUpload('This PDF has no pages.', code='UNSUPPORTED_MEDIA_TYPE', status=415)
        if pages > MAX_PDF_PAGES:
            raise InvalidUpload(f'This PDF has {pages} pages. Upload only the relevant pages (up to {MAX_PDF_PAGES}).', code='PDF_TOO_LONG', status=413)
        parts, total = [], 0
        for pg in r.pages:
            try:
                t = pg.extract_text() or ''
            except Exception:  # noqa: BLE001 - one bad page must not reject the file
                t = ''
            parts.append(t); total += len(t)
            if total > MAX_TEXT_CHARS * 2:
                break
    except InvalidUpload:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError, RecursionError):
        raise InvalidUpload('This PDF could not be read. It may be damaged.', code='UNSUPPORTED_MEDIA_TYPE', status=415)
    text, truncated = _clip('\n\n'.join(parts))
    return Processed('document', 'application/pdf', 'pdf', data, meta={'filename': name, 'pages': pages, 'text': text, 'text_chars': len(text),
                                                                      'text_truncated': truncated, 'scanned': len(text) < 20 * pages})


def process_docx(data: bytes, name: str) -> Processed:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            info = z.getinfo('word/document.xml')
            if info.file_size > MAX_DOCX_XML_BYTES:
                raise InvalidUpload('This Word document is too large to read.', code='UPLOAD_TOO_LARGE', status=413)
            xml = z.read(info).decode('utf-8', 'replace')
    except InvalidUpload:
        raise
    except (zipfile.BadZipFile, KeyError, OSError, RuntimeError):
        raise InvalidUpload('This is not a valid Word (.docx) document.', code='UNSUPPORTED_MEDIA_TYPE', status=415)
    xml = re.sub(r'</w:p>', '\n', xml)
    xml = re.sub(r'<w:tab/>', '\t', xml)
    text = re.sub(r'<[^>]+>', '', xml)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&apos;', "'")
    text, truncated = _clip(text)
    if not text:
        raise InvalidUpload('This Word document has no readable text.', code='UNSUPPORTED_MEDIA_TYPE', status=415)
    return Processed('document', DOCX_MIME, 'docx', data, meta={'filename': name, 'text': text, 'text_chars': len(text), 'text_truncated': truncated})


def process_text(data: bytes, name: str, ext: str) -> Processed:
    if b'\x00' in data[:100_000]:
        raise InvalidUpload('This file is not plain text.', code='UNSUPPORTED_MEDIA_TYPE', status=415)
    try:
        raw = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise InvalidUpload('Text files must be UTF-8 encoded.', code='UNSUPPORTED_MEDIA_TYPE', status=415)
    text, truncated = _clip(raw)
    if not text:
        raise InvalidUpload('This text file is empty.', code='INVALID_UPLOAD')
    return Processed('document', TEXT_TYPES[ext], ext, data, meta={'filename': name, 'text': text, 'text_chars': len(text), 'text_truncated': truncated})


def process_upload(data: bytes, filename: str | None) -> Processed:
    """Route by content signature first, then by extension for text-like files."""
    if not data:
        raise InvalidUpload('Empty file.')
    name = safe_name(filename, 'file')
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    head = data[:16]
    if head.startswith(b'%PDF-'):
        kind = 'document'
    elif head.startswith(b'PK\x03\x04') and ext == 'docx':
        kind = 'document'
    elif ext in TEXT_TYPES and not head.startswith((b'\x89PNG', b'\xff\xd8', b'RIFF', b'PK')):
        kind = 'document'
    else:
        kind = 'image'
    if len(data) > _limit_bytes(kind):
        mb = _limit_bytes(kind) // (1024 * 1024)
        raise InvalidUpload(f'{"Document" if kind == "document" else "Image"} is larger than {mb} MB.', code='UPLOAD_TOO_LARGE', status=413)
    if head.startswith(b'%PDF-'):
        return process_pdf(data, name)
    if kind == 'document' and ext == 'docx':
        return process_docx(data, name)
    if kind == 'document':
        return process_text(data, name, ext)
    try:
        return process_image(data)
    except InvalidUpload as e:
        if e.code == 'UNSUPPORTED_MEDIA_TYPE':
            raise InvalidUpload(f'That file type is not supported. {SUPPORTED_HINT}', code='UNSUPPORTED_MEDIA_TYPE', status=415) from None
        raise
