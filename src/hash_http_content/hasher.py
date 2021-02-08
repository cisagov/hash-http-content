"""Functionality to get a hash of an HTTP URL's visible content."""

# Standard Python Libraries
import hashlib


def get_hasher(hash_algorithm: str) -> "hashlib._Hash":
    """Get a hashing object."""
    # Not all implementations support the "usedforsecurity" keyword argument,
    # which is used to indicate that the algorithm is being used for non-security
    # related tasks. This is required for some algorithms on FIPS systems.
    try:
        hasher = getattr(hashlib, hash_algorithm)(usedforsecurity=False)
    except AttributeError:
        # There is no named constructor for the desired hashing algorithm
        try:
            # Work around typeshed's incorrect type hints
            hasher = getattr(hashlib, "new")(hash_algorithm, usedforsecurity=False)
        except TypeError:
            hasher = hashlib.new(hash_algorithm)
    except TypeError:
        hasher = getattr(hashlib, hash_algorithm)()
    return hasher


def get_hash_digest(hash_algorithm: str, contents: bytes) -> str:
    """Get a hex digest representing a hash of the given contents."""
    hasher: "hashlib._Hash" = get_hasher(hash_algorithm)
    hasher.update(contents)
    return hasher.hexdigest()
