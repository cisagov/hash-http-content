#!/usr/bin/env pytest -vs
"""Tests for hash_http_content URL hashing functionality."""

# Standard Python Libraries
import hashlib
import json
import os.path

# Third-Party Libraries
from bs4 import Comment, Tag
import pytest

# cisagov Libraries
import hash_http_content

# Hashing algorithm to use for testing.
HASH_ALGORITHM = "sha256"
# Alternate encoding to verify conversion to utf-8
ALT_ENCODING = "utf-16"
# Files with test values
TEST_VALUE_SOURCES = {
    "html_dynamic": "tests/files/testing_dynamic.html",
    "html_dynamic_bytes": "tests/files/testing_html_dynamic.bin",
    "html_static": "tests/files/testing_static.html",
    "html_static_bytes": "tests/files/testing_html_static.bin",
    "json": "tests/files/testing.json",
    "plaintext": "tests/files/testing.txt",
    "raw_bytes": "tests/files/testing.bin",
}
# Digests expected for each test
EXPECTED_DIGESTS = {
    "html_dynamic": "3a6f9739ba635b5bfe57246ebf137f00df890a200b6dca01388f05d81479098a",
    "html_static": "206794946ac5783ddbaa03713fe9eba7be069d970731b20a7f6cadb5d845680f",
    "json": "25ba3da8ab38c80c8d1e6162caeb1924a777b04b7351ce31176f7bef9cd6584d",
    "plaintext": "d09107e7b64bee9d7375d734a7bfc9cc316d7c48695722be3ec2218659d59be5",
    "raw_bytes": "5f78c33274e43fa9de5659265c1d917e25c03722dcb0b8d27db8d5feaa813953",
}


@pytest.mark.parametrize("algorithm", hashlib.algorithms_available)
def test_get_hasher(algorithm):
    """Verify that the desired hashing object is created."""
    assert hash_http_content.hasher.get_hasher(algorithm).name == algorithm


def test_hash_hash_digest():
    """Verify that an expected hash digest is generated."""
    expected_digest = "d5f8f30f25636b1f3efc2f52a0a8724c9ffa280875a1fc9a92cfe3f644b7d5c3"
    digest = hash_http_content.hasher.get_hash_digest(HASH_ALGORITHM, b"cisagov")
    assert digest == expected_digest


def test_init_browser():
    """Ensure that a browser object is initialized."""
    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    assert hasher._browser is None
    # Call through name mangling
    hasher._UrlHasher__init_browser()
    assert hasher._browser is not None


@pytest.mark.parametrize(
    "tag,expected",
    [
        (Tag(name="html", parent=Tag(name="[document]")), False),
        (Tag(name="", parent=Tag(name="script")), False),
        (Tag(name="", parent=Tag(name="style")), False),
        (Comment("Testing page."), False),
        (Tag(name="", parent=Tag(name="title")), True),
        (Tag(name="", parent=Tag(name="p")), True),
    ],
)
def test__is_visible_element(tag, expected):
    """Verify that elements are correctly identified as visible or not."""
    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    assert hasher._is_visible_element(tag) == expected


def test_handle_raw_bytes():
    """Test the handler for bytes of an unspecified format and encoding."""
    with open(TEST_VALUE_SOURCES["raw_bytes"], "rb") as f:
        # Work around the end-of-file-fixer pre-commit hook
        test_bytes = f.read().rstrip()

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_raw_bytes(test_bytes, None)

    assert result.hash == EXPECTED_DIGESTS["raw_bytes"]
    assert result.contents == test_bytes


def test_handle_plaintext():
    """Test the handler with plaintext in utf-8 encoding."""
    with open(TEST_VALUE_SOURCES["plaintext"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, "utf-8")

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_plaintext(test_bytes, None)

    assert result.hash == EXPECTED_DIGESTS["plaintext"]
    assert result.contents == test_bytes


def test_handle_plaintext_with_encoding():
    """Test the handler converting to utf-8 encoding."""
    with open(TEST_VALUE_SOURCES["plaintext"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, ALT_ENCODING)
    expected_bytes = bytes(test_value, "utf-8")

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_plaintext(test_bytes, ALT_ENCODING)

    assert result.hash == EXPECTED_DIGESTS["plaintext"]
    assert result.contents == expected_bytes


def test_handle_json():
    """Test the handler with JSON in utf-8 encoding."""
    with open(TEST_VALUE_SOURCES["json"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, "utf-8")
    expected_bytes = bytes(
        json.dumps(json.loads(test_value), separators=(",", ":"), sort_keys=True),
        "utf-8",
    )

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_json(test_bytes, None)

    assert result.hash == EXPECTED_DIGESTS["json"]
    assert result.contents == expected_bytes


def test_handle_json_with_encoding():
    """Test the handler converting JSON to utf-8 encoding."""
    with open(TEST_VALUE_SOURCES["json"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, ALT_ENCODING)
    expected_bytes = bytes(
        json.dumps(json.loads(test_value), separators=(",", ":"), sort_keys=True),
        "utf-8",
    )

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_json(test_bytes, ALT_ENCODING)

    assert result.hash == EXPECTED_DIGESTS["json"]
    assert result.contents == expected_bytes


def test_handle_html_static():
    """Test the handler with static HTML in utf-8 encoding."""
    with open(TEST_VALUE_SOURCES["html_static"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, "utf-8")
    with open(TEST_VALUE_SOURCES["html_static_bytes"], "rb") as f:
        # Work around the end-of-file-fixer pre-commit hook
        expected_bytes = f.read().rstrip()

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_html(test_bytes, None)

    assert result.hash == EXPECTED_DIGESTS["html_static"]
    assert result.contents == expected_bytes


def test_handle_html_static_with_encoding():
    """Test the handler converting static HTML to utf-8 encoding."""
    with open(TEST_VALUE_SOURCES["html_static"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, ALT_ENCODING)
    with open(TEST_VALUE_SOURCES["html_static_bytes"], "rb") as f:
        # Work around the end-of-file-fixer pre-commit hook
        expected_bytes = f.read().rstrip()

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_html(test_bytes, ALT_ENCODING)

    assert result.hash == EXPECTED_DIGESTS["html_static"]
    assert result.contents == expected_bytes


def test_handle_html_dynamic():
    """Test the handler with dynamic HTML in utf-8 encoding."""
    with open(TEST_VALUE_SOURCES["html_dynamic"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, "utf-8")
    with open(TEST_VALUE_SOURCES["html_dynamic_bytes"], "rb") as f:
        # Work around the end-of-file-fixer pre-commit hook
        expected_bytes = f.read().rstrip()

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_html(test_bytes, None)

    assert result.hash == EXPECTED_DIGESTS["html_dynamic"]
    assert result.contents == expected_bytes


def test_handle_html_dynmamic_with_encoding():
    """Test the handler converting dynamic HTML to utf-8 encoding."""
    with open(TEST_VALUE_SOURCES["html_dynamic"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, ALT_ENCODING)
    with open(TEST_VALUE_SOURCES["html_dynamic_bytes"], "rb") as f:
        # Work around the end-of-file-fixer pre-commit hook
        expected_bytes = f.read().rstrip()

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher._handle_html(test_bytes, ALT_ENCODING)

    assert result.hash == EXPECTED_DIGESTS["html_dynamic"]
    assert result.contents == expected_bytes


def test_hash_url_html_status_200():
    """Test againt a URL that returns HTML content from an existing location."""
    test_url = "https://example.com"
    expected_digest = "6fba1a7167467b6dd3da090b5ec437c1b811dd2c2133504a448fb7ca59d390c2"

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher.hash_url(test_url)

    assert result.status == 200
    assert result.is_redirect is False
    assert result.hash == expected_digest


def test_hash_url_html_status_404():
    """Test against a URL that returns HTML content from a missing location."""
    test_url = "https://example.com/404"
    expected_digest = "6fba1a7167467b6dd3da090b5ec437c1b811dd2c2133504a448fb7ca59d390c2"

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher.hash_url(test_url)

    assert result.status == 404
    assert result.is_redirect is False
    assert result.hash == expected_digest


def test_hash_url_with_redirect():
    """Test against a URL that redirects and has no content-type parameters."""
    test_url = "http://rules.ncats.cyber.dhs.gov"

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM)
    result = hasher.hash_url(test_url)

    assert result.status == 200
    assert result.is_redirect is True


def test_browser_additional_options():
    """Verify that additional options are used in invoking the browser."""
    # These options are expected for a lambda style environment
    options = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--single-process",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-zygote",
        ],
        "executablePath": "tests/files/serverless-chrome",
    }
    with open(TEST_VALUE_SOURCES["plaintext"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, ALT_ENCODING)
    expected_bytes = bytes(test_value, "utf-8")

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM, browser_options=options)
    result = hasher._handle_plaintext(test_bytes, ALT_ENCODING)

    assert hasher._UrlHasher__browser_options == options
    assert result.hash == EXPECTED_DIGESTS["plaintext"]
    assert result.contents == expected_bytes


def test_browser_with_specified_executable():
    """Test running with the executablePath option."""
    serverless_chrome_path = "tests/files/headless-chromium"
    # If this file does not exist, do not perform this test.
    if not os.path.isfile(serverless_chrome_path):
        pytest.skip("no serverless-chrome binary found")

    # These options are expected for a lambda style environment
    options = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--single-process",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-zygote",
        ],
        "executablePath": serverless_chrome_path,
    }

    with open(TEST_VALUE_SOURCES["plaintext"]) as f:
        test_value = f.read()
    test_bytes = bytes(test_value, ALT_ENCODING)
    expected_bytes = bytes(test_value, "utf-8")

    hasher = hash_http_content.UrlHasher(HASH_ALGORITHM, browser_options=options)
    result = hasher._handle_plaintext(test_bytes, ALT_ENCODING)

    assert hasher._UrlHasher__browser_options == options
    assert result.hash == EXPECTED_DIGESTS["plaintext"]
    assert result.contents == expected_bytes
