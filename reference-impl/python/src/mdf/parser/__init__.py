"""MDF XML parser — public API.

Functions
---------
parse_file(path)
    Parse a ``.mdf`` or ``.mdfx`` file from the filesystem.
parse_string(xml)
    Parse MDF XML from a string or bytes in memory.

Exceptions
----------
MDFParseError
    Raised for structurally invalid MDF documents.

Content element types (populated inside ``Layer.elements``)
-----------------------------------------------------------
TextBlock, TextParagraph, TextSpan, ReflowRegion
ShapeElement, ImageElement, Group
"""

from mdf.parser.mdf_parser import (
    MDFParseError,
    Group,
    ImageElement,
    ReflowRegion,
    ShapeElement,
    TextBlock,
    TextParagraph,
    TextSpan,
    parse_file,
    parse_string,
)

__all__ = [
    "parse_file",
    "parse_string",
    "MDFParseError",
    # content element types
    "TextBlock",
    "TextParagraph",
    "TextSpan",
    "ReflowRegion",
    "ShapeElement",
    "ImageElement",
    "Group",
]
