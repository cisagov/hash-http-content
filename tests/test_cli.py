#!/usr/bin/env pytest -vs
"""Tests for hash_http_content command line interface."""

# Standard Python Libraries
import hashlib
import json
import os
import sys
from unittest.mock import patch

# Third-Party Libraries
import pytest

# cisagov Libraries
from hash_http_content import __version__, cli

# define sources of version strings
RELEASE_TAG = os.getenv("RELEASE_TAG")
PROJECT_VERSION = __version__


def test_stdout_version(capsys):
    """Verify that version string sent to stdout agrees with the module version."""
    with pytest.raises(SystemExit):
        with patch.object(sys, "argv", ["bogus", "--version"]):
            cli.main()
    captured = capsys.readouterr()
    assert (
        captured.out == f"{PROJECT_VERSION}\n"
    ), "standard output by '--version' should agree with module.__version__"


def test_running_as_module(capsys):
    """Verify that the __main__.py file loads correctly."""
    with pytest.raises(SystemExit):
        with patch.object(sys, "argv", ["bogus", "--version"]):
            # F401 is a "Module imported but unused" warning. This import
            # emulates how this project would be run as a module. The only thing
            # being done by __main__ is importing the main entrypoint of the
            # package and running it, so there is nothing to use from this
            # import. As a result, we can safely ignore this warning.
            # cisagov Libraries
            import hash_http_content.__main__  # noqa: F401
    captured = capsys.readouterr()
    assert (
        captured.out == f"{PROJECT_VERSION}\n"
    ), "standard output by '--version' should agree with module.__version__"


@pytest.mark.skipif(
    RELEASE_TAG in [None, ""], reason="this is not a release (RELEASE_TAG not set)"
)
def test_release_version():
    """Verify that release tag version agrees with the module version."""
    assert (
        RELEASE_TAG == f"v{PROJECT_VERSION}"
    ), "RELEASE_TAG does not match the project version"


def test_list_algorithms(capsys):
    """Validate a matching list of algorithms is returned."""
    expected_output = "Algorithms supported for this platform:\n" + "\n".join(
        f"- {a}" for a in sorted(hashlib.algorithms_available)
    )
    return_code = None
    with patch.object(sys, "argv", ["bogus", "--list-algorithms"]):
        return_code = cli.main()
    captured = capsys.readouterr()
    assert return_code is None
    assert captured.out.rstrip() == expected_output


def test_invalid_hash_type(capsys):
    """Validate that an unsupported hash type causes an error."""
    expected_output = f"Invalid algorithm provided. Must be one of: {sorted(hashlib.algorithms_available)}"
    return_code = None
    try:
        with patch.object(
            sys, "argv", ["bogus", "--hash-algorithm", "nonsensical", "localhost"]
        ):
            return_code = cli.main()
    except SystemExit as sys_exit:
        return_code = sys_exit.code
    captured = capsys.readouterr()
    assert return_code == 1
    assert captured.err.rstrip() == expected_output


def test_full_run_no_http_schema(capsys):
    """Validate output for a given URL with no schema."""
    expected_output = "\n".join(
        [
            "Results for example.com:",
            "  Retrieved URL - 'https://example.com/'",
            "  Status code - '200'",
            "  Content type - 'text/html'",
            "  Hash (sha256) of contents - 6fba1a7167467b6dd3da090b5ec437c1b811dd2c2133504a448fb7ca59d390c2",
        ]
    )
    return_code = None
    try:
        with patch.object(sys, "argv", ["bogus", "example.com"]):
            return_code = cli.main()
    except SystemExit as sys_exit:
        return_code = sys_exit.code
    captured = capsys.readouterr()

    assert return_code is None
    assert captured.out.rstrip() == expected_output


def test_full_run_with_http_schema(capsys):
    """Validate output for a given URL with a provided schema."""
    expected_output = "\n".join(
        [
            "Results for https://example.com:",
            "  Retrieved URL - 'https://example.com/'",
            "  Status code - '200'",
            "  Content type - 'text/html'",
            "  Hash (sha256) of contents - 6fba1a7167467b6dd3da090b5ec437c1b811dd2c2133504a448fb7ca59d390c2",
        ]
    )
    return_code = None
    try:
        with patch.object(sys, "argv", ["bogus", "https://example.com"]):
            return_code = cli.main()
    except SystemExit as sys_exit:
        return_code = sys_exit.code

    captured = capsys.readouterr()

    assert return_code is None
    assert captured.out.rstrip() == expected_output


def test_full_run_no_redirect(capsys):
    """Validate output for a given URL that has no redirect."""
    expected_output = [
        "Results for http://example.com:",
        "  Retrieved URL - 'http://example.com/'",
        "  Status code - '200'",
        "  Content type - 'text/html'",
        "  Redirect - False",
    ]
    return_code = None
    try:
        with patch.object(
            sys, "argv", ["bogus", "--show-redirect", "http://example.com"]
        ):
            return_code = cli.main()
    except SystemExit as sys_exit:
        return_code = sys_exit.code

    captured = capsys.readouterr()
    captured_lines = captured.out.split("\n")

    assert return_code is None

    for i, value in enumerate(expected_output):
        assert captured_lines[i] == value


def test_full_run_with_redirect(capsys):
    """Validate output for a given URL that has a redirect."""
    expected_output = [
        "Results for http://rules.ncats.cyber.dhs.gov:",
        "  Retrieved URL - 'https://rules.ncats.cyber.dhs.gov/'",
        "  Status code - '200'",
        "  Content type - 'text/plain'",
        "  Redirect - True",
    ]
    return_code = None
    try:
        with patch.object(
            sys,
            "argv",
            ["bogus", "--show-redirect", "http://rules.ncats.cyber.dhs.gov"],
        ):
            return_code = cli.main()
    except SystemExit as sys_exit:
        return_code = sys_exit.code

    captured = capsys.readouterr()
    captured_lines = captured.out.split("\n")

    assert return_code is None

    for i, value in enumerate(expected_output):
        assert captured_lines[i] == value


def test_full_run_with_content(capsys):
    """Validate output with content for a given URL."""
    expected_output = "\n".join(
        [
            "Results for https://example.com:",
            "  Retrieved URL - 'https://example.com/'",
            "  Status code - '200'",
            "  Content type - 'text/html'",
            "  Hash (sha256) of contents - 6fba1a7167467b6dd3da090b5ec437c1b811dd2c2133504a448fb7ca59d390c2",
            "",
            "Contents:",
            r"b'Example Domain Example Domain This domain is for use in illustrative examples in documents. You may use this\n    domain in literature without prior coordination or asking for permission. More information...'",
        ]
    )
    return_code = None
    try:
        with patch.object(
            sys, "argv", ["bogus", "--show-content", "https://example.com"]
        ):
            return_code = cli.main()
    except SystemExit as sys_exit:
        return_code = sys_exit.code

    captured = capsys.readouterr()

    assert return_code is None
    assert captured.out.rstrip() == expected_output


def test_full_run_check_redirect_with_content(capsys):
    """Validate output with content for a given URL with redirect check."""
    expected_output = "\n".join(
        [
            "Results for https://example.com:",
            "  Retrieved URL - 'https://example.com/'",
            "  Status code - '200'",
            "  Content type - 'text/html'",
            "  Redirect - False",
            "  Hash (sha256) of contents - 6fba1a7167467b6dd3da090b5ec437c1b811dd2c2133504a448fb7ca59d390c2",
            "",
            "Contents:",
            r"b'Example Domain Example Domain This domain is for use in illustrative examples in documents. You may use this\n    domain in literature without prior coordination or asking for permission. More information...'",
        ]
    )
    return_code = None
    try:
        with patch.object(
            sys,
            "argv",
            ["bogus", "--show-content", "--show-redirect", "https://example.com"],
        ):
            return_code = cli.main()
    except SystemExit as sys_exit:
        return_code = sys_exit.code

    captured = capsys.readouterr()

    assert return_code is None
    assert captured.out.rstrip() == expected_output


def test_full_run_json_output(capsys):
    """Validate JSON output for a given URL."""
    expected_result = [
        {
            "content_type": "text/html",
            "contents_hash": "6fba1a7167467b6dd3da090b5ec437c1b811dd2c2133504a448fb7ca59d390c2",
            "is_redirected": False,
            "requested_url": "https://example.com",
            "retrieved_url": "https://example.com/",
            "status_code": 200,
        }
    ]
    return_code = None
    try:
        with patch.object(sys, "argv", ["bogus", "--json", "https://example.com"]):
            return_code = cli.main()
    except SystemExit as sys_exit:
        return_code = sys_exit.code

    captured = capsys.readouterr()

    captured_result = json.loads(captured.out)

    assert return_code is None
    assert captured_result == expected_result
