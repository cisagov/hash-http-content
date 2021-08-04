"""Command line interface to the hash-http-content package.

Usage:
  site-hash [--hash-algorithm=algorithm] ([--show-content] [--show-redirect] | [--json]) URL ...
  site-hash --list-algorithms
  site-hash (-v | --version)
  site-hash (-h | --help)

Options:
  -h, --help                      Display this help text.
  -a, --hash-algorithm=algorithm  Use the provided hash alogorithm.
                                  [default: sha256]
  -l, --list-algorithms           List available hash algorithms.
  -j, --json                      Output the results as a JSON.
  -c, --show-content              Output the content after processing.
  -r, --show-redirect             Output if the requested URL was redirected.
  -v, --version                   Show version information.
"""

# Standard Python Libraries
import hashlib
from json import dumps
import sys
from typing import Any, Dict
from urllib.parse import urlparse

# Third-Party Libraries
import docopt
from schema import And, Schema, SchemaError, Use

from ._version import __version__
from .hasher import UrlHasher


def main() -> None:
    """Return the hash(es) and information from the requested URL(s)."""
    args: Dict[str, str] = docopt.docopt(__doc__, version=__version__)
    schema: Schema = Schema(
        {
            "--hash-algorithm": And(
                str,
                Use(str.lower),
                lambda a: a in hashlib.algorithms_available,
                error=f"Invalid algorithm provided. Must be one of: {sorted(hashlib.algorithms_available)}",
            ),
            str: object,
        }
    )

    try:
        validated_args: Dict[str, Any] = schema.validate(args)
    except SchemaError as err:
        # Exit because one or more of the arguments were invalid
        print(err, file=sys.stderr)
        sys.exit(1)

    if validated_args["--list-algorithms"]:
        print("Algorithms supported for this platform:")
        for algo in sorted(hashlib.algorithms_available):
            print(f"- {algo}")
        return

    if validated_args["--json"]:
        results = []

    for url in validated_args["URL"]:
        # Prefer an HTTPS URL
        parsed_url = urlparse(url, "https")
        if not parsed_url.netloc:
            parsed_url = parsed_url._replace(netloc=parsed_url.path, path="")

        hasher = UrlHasher(validated_args["--hash-algorithm"])
        url_results = hasher.hash_url(parsed_url.geturl())

        if validated_args["--json"]:
            # We cannot guarantee that the contents are serializable, so they are
            # excluded from JSON results.
            results.append(
                {
                    "content_type": url_results.content_type,
                    "contents_hash": url_results.hash,
                    "is_redirected": url_results.is_redirect,
                    "requested_url": url,
                    "retrieved_url": url_results.visited_url,
                    "status_code": url_results.status,
                }
            )
        else:
            print(f"Results for {url}:")
            print(f"  Retrieved URL - '{url_results.visited_url}'")
            print(f"  Status code - '{url_results.status}'")
            print(f"  Content type - '{url_results.content_type}'")
            if validated_args["--show-redirect"]:
                print(f"  Redirect - {url_results.is_redirect}")
            print(
                f"  Hash ({validated_args['--hash-algorithm']}) of contents - {url_results.hash}"
            )
            if validated_args["--show-content"]:
                print()
                print("Contents:")
                print(url_results.contents)
            print()

    if validated_args["--json"]:
        print(dumps(results, separators=(",", ":"), sort_keys=True))
