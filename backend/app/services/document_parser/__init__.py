from app.services.document_parser.docx_parser import DocxParser
from app.services.document_parser.pdf_parser import PdfParser


def get_parser_for(filename: str, mime_type: str):
    for parser in (DocxParser(), PdfParser()):
        if parser.can_parse(filename, mime_type):
            return parser
    return None
