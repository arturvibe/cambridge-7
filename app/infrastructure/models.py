"""
Pydantic models for the infrastructure layer.
"""

from pydantic import BaseModel


class FrameioFile(BaseModel):
    """
    Represents a file retrieved from the Frame.io API.
    """

    url: str
    name: str
