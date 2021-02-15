"""Functionality to get a hash of an HTTP URL's visible content."""

# Standard Python Libraries
import asyncio
import hashlib
import json
import logging
import tempfile
from typing import Any, Callable, Dict, NamedTuple

# Third-Party Libraries
from bs4 import BeautifulSoup
from bs4.element import Comment, PageElement
from pyppeteer import launch
from pyppeteer.browser import Browser
from pyppeteer.errors import TimeoutError
from pyppeteer.page import Page
import requests


def get_hasher(hash_algorithm: str) -> "hashlib._Hash":
    """Get a hashing object."""
    logging.debug("Creating a %s hashing object", hash_algorithm)
    # Not all implementations support the "usedforsecurity" keyword argument,
    # which is used to indicate that the algorithm is being used for non-security
    # related tasks. This is required for some algorithms on FIPS systems.
    try:
        hasher = getattr(hashlib, hash_algorithm)(usedforsecurity=False)
    except AttributeError:
        # There is no named constructor for the desired hashing algorithm
        try:
            # mypy relies on typeshed (https://github.com/python/typeshed) for
            # stdlib type hinting, but it does not have the correct type hints for
            # hashlib.new(). The PR I submitted to fix them
            # (https://github.com/python/typeshed/pull/4973) was approved, but I
            # am not sure if mypy will still have issues with the usage of this
            # keyword in non Python 3.9 (when the usedforsecurity kwarg was added)
            # environments. I believe the earliest I can test this will be in mypy
            # v0.900, and I have made
            # https://github.com/cisagov/hash-http-content/issues/3 to document
            # the status of this workaround.
            # hasher = hashlib.new(hash_algorithm, usedforsecurity=False)
            hasher = getattr(hashlib, "new")(hash_algorithm, usedforsecurity=False)
        except TypeError:
            hasher = hashlib.new(hash_algorithm)
    except TypeError:
        hasher = getattr(hashlib, hash_algorithm)()
    return hasher


def get_hash_digest(hash_algorithm: str, contents: bytes) -> str:
    """Get a hex digest representing a hash of the given contents."""
    logging.debug(
        "Generating a %s digest for provided content of length %d",
        hash_algorithm,
        len(contents),
    )
    hasher: "hashlib._Hash" = get_hasher(hash_algorithm)
    hasher.update(contents)
    return hasher.hexdigest()


class HandlerResult(NamedTuple):
    """Named tuple to store the result of a handler call."""

    hash: str
    contents: bytes


class UrlResult(NamedTuple):
    """Named tuple to store the result of a SiteHasher.hash_url() call."""

    status: int
    visited_url: str
    is_redirect: bool
    content_type: str
    hash: str
    contents: bytes


class UrlHasher:
    """Provide functionality to get the hash digest of a given URL."""

    def __init__(
        self,
        hash_algorithm: str,
        encoding: str = "utf-8",
        browser_options: Dict[str, Any] = {},
    ):
        """Initialize an instance of this class."""
        logging.debug("Initializing UrlHasher object")
        default_browser_options = {"headless": True}
        logging.debug("Default browser options: %s", default_browser_options)

        # Number of retries
        self._retries = 3
        logging.debug("Using retry value of '%d'", self._retries)

        # Timeout in seconds
        self._timeout = 5
        logging.debug("Using request timeout limit of '%d' seconds", self._timeout)

        self.__browser_options = {**default_browser_options, **browser_options}
        logging.debug("Using browser options: %s", self.__browser_options)

        self._browser: Browser = None
        self._browser_page: Page = None
        self._default_encoding = encoding
        self._hash_algorithm = hash_algorithm

        logging.debug("Using default encoding '%s'", self._default_encoding)
        logging.debug("Using hashing algorithm '%s'", self._hash_algorithm)

        self._handlers: Dict[str, Callable] = {
            "application/json": self._handle_json,
            "text/html": self._handle_html,
            "text/plain": self._handle_plaintext,
        }

    def __init_browser(self):
        """Initialize the pyppeteer Browser if it does not exist."""
        if not self._browser:
            logging.debug("Initializing Browser object")
            self._browser = asyncio.get_event_loop().run_until_complete(
                launch(**self.__browser_options)
            )
            self._browser_page = asyncio.get_event_loop().run_until_complete(
                self._browser.newPage()
            )

    def _is_visible_element(self, element: PageElement) -> bool:
        """Return True if the given website element would be visible."""
        discard_tags = ["[document]", "script", "style"]
        if isinstance(element, Comment):
            logging.debug("Skipping Comment tag")
            return False
        if element.parent.name in discard_tags:
            logging.debug("Skipping element in parent tag '%s'", element.parent.name)
            return False
        return True

    def _handle_raw_bytes(self, contents: bytes, encoding: str) -> HandlerResult:
        """Handle bytes in an unspecified format or encoding."""
        logging.debug("Handling content as raw bytes")
        digest: str = get_hash_digest(self._hash_algorithm, contents)
        return HandlerResult(digest, contents)

    def _handle_plaintext(self, contents: bytes, encoding: str) -> HandlerResult:
        """Handle plaintext contents."""
        logging.debug("Handling content as plaintext")
        if encoding:
            contents = bytes(contents.decode(encoding), self._default_encoding)
        digest: str = get_hash_digest(self._hash_algorithm, contents)
        return HandlerResult(digest, contents)

    def _handle_json(self, contents: bytes, encoding: str) -> HandlerResult:
        """Handle JSON contents."""
        logging.debug("Handling content as JSON")
        # Translate the original encoding to utf-8
        if encoding:
            json_str = str(contents, encoding)
        else:
            json_str = str(contents, self._default_encoding)

        json_data = json.loads(json_str)
        # Sort the keys to make this deterministic
        json_bytes = bytes(
            json.dumps(json_data, separators=(",", ":"), sort_keys=True),
            self._default_encoding,
        )

        digest: str = get_hash_digest(self._hash_algorithm, json_bytes)

        return HandlerResult(digest, json_bytes)

    def _handle_html(self, contents: bytes, encoding: str) -> HandlerResult:
        """Handle an HTML page."""
        logging.debug("Handling content as HTML")
        self.__init_browser()

        # Until the Page.setContent() method allows options, writing the HTML
        # document to a temporary file and navigating to it with Page.goto() is
        # the only way to leverage the `waitUntil` option to give time for the
        # page's contents to load. Support for options in Page.setContent() is
        # expected in pyppeteer when the puppeteer v2.1.1 feature parity rewrite
        # is completed per:
        # https://github.com/pyppeteer/pyppeteer/issues/134 for more information
        with tempfile.NamedTemporaryFile(suffix=".html") as fp:
            # Output to a temporary file so it's available to the browser
            fp.write(contents)
            fp.flush()

            logging.debug("Navigating to temporary file '%s'", fp.name)

            try:
                # Wait for everything to load after navigating to the temporary file
                asyncio.get_event_loop().run_until_complete(
                    self._browser_page.goto(
                        f"file://{fp.name}",
                        # Wait for load and networkidle2 events up to the given
                        # timeout of five seconds (in milliseconds)
                        {"timeout": 5000, "waitUntil": ["load", "networkidle2"]},
                    )
                )
            # Waiting for load and networkidle2 events to occur exceeded the
            # configured timeout
            except TimeoutError:
                pass
            page_contents: str = asyncio.get_event_loop().run_until_complete(
                self._browser_page.content()
            )

        # Try to guarantee our preferred encoding
        page_contents = bytes(page_contents.encode(self._default_encoding)).decode(
            self._default_encoding
        )

        logging.debug("Parsing rendered page contents")
        soup: BeautifulSoup = BeautifulSoup(page_contents, "lxml")
        text_elements = soup.find_all(text=True)
        visible_text_elements = filter(self._is_visible_element, text_elements)
        visible_text = " ".join(t.strip() for t in visible_text_elements if t.strip())
        visible_bytes = bytes(visible_text, self._default_encoding)

        digest: str = get_hash_digest(self._hash_algorithm, visible_bytes)

        return HandlerResult(digest, visible_bytes)

    def hash_url(self, url: str) -> UrlResult:
        """Get a hash of the contents of the provided URL."""
        logging.debug("Hashing provided URL '%s'", url)

        # These values were chosen to keep in line with the type of redirection
        # that indicates the desired resource is at a different URI per
        # https://tools.ietf.org/html/rfc7231#section-6.4
        # 1. Redirects that indicate the resource might be available at a
        #    different URI, as provided by the Location field, as in the
        #    status codes 301 (Moved Permanently), 302 (Found), and 307
        #    (Temporary Redirect).
        # This follows the logic in the creation of status code 308 per
        # https://tools.ietf.org/html/rfc7238#section-1
        redirect_status_codes = [301, 302, 307, 308]

        # Attempt to retrieve the given URL, retrying self._retries times before
        # raising an exception
        get_tries = 0
        while True:
            try:
                resp = requests.get(url, timeout=self._timeout)
                break
            except Exception as err:
                get_tries += 1
                if get_tries <= self._retries:
                    logging.warning(
                        "Performing retry %d/%d for '%s'", get_tries, self._retries, url
                    )
                else:
                    raise err

        # https://tools.ietf.org/html/rfc7231#section-3.1.1.5
        content_type = (
            resp.headers.get("content-type", "application/octet-stream").strip().lower()
        )

        # Pull off any parameters included
        if ";" in content_type:
            content_type = content_type.split(";", 1)[0]
        logging.debug("Using content type '%s'", content_type)

        logging.debug("Checking for a redirect in the request")
        is_redirect = False
        for r in resp.history:
            if r.status_code in redirect_status_codes:
                is_redirect = True
                break

        processed: HandlerResult
        # If the content appears to be text, we should fall back to processing it
        # as plaintext instead of raw bytes.
        if resp.apparent_encoding == "ascii":
            # Default to processing as plaintext if no appropriate handler is found
            processed = self._handlers.get(content_type, self._handle_plaintext)(
                resp.content, resp.encoding
            )
        else:
            # Default to processing as raw bytes if no appropriate handler is found
            processed = self._handlers.get(content_type, self._handle_raw_bytes)(
                resp.content, resp.encoding
            )

        return UrlResult(
            resp.status_code,
            resp.url,
            is_redirect,
            content_type,
            processed.hash,
            processed.contents,
        )
