from bs4 import BeautifulSoup

from spyke.infrastructure.sources.http import HttpDocument


def get_soup(document: HttpDocument) -> BeautifulSoup:
    """
    Convert an HttpDocument to a BeautifulSoup object.

    Args:
        document (HttpDocument): The HTTP document to convert.

    Returns:
        BeautifulSoup: A BeautifulSoup object representing the HTML content of the document.
    """
    return BeautifulSoup(document.body, "html.parser")
