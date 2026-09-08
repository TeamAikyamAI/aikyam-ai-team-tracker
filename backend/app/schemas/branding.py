from pydantic import BaseModel


class LogoMeta(BaseModel):
    """Everything the frontend needs to render the logo and bust its cache."""
    has_custom: bool
    version: str
    url: str
    content_type: str
    filename: str
    size_bytes: int
