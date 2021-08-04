# hash-http-content #

[![GitHub Build Status](https://github.com/cisagov/hash-http-content/workflows/build/badge.svg)](https://github.com/cisagov/hash-http-content/actions)
[![Coverage Status](https://coveralls.io/repos/github/cisagov/hash-http-content/badge.svg?branch=develop)](https://coveralls.io/github/cisagov/hash-http-content?branch=develop)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/cisagov/hash-http-content.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/hash-http-content/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/cisagov/hash-http-content.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/hash-http-content/context:python)
[![Known Vulnerabilities](https://snyk.io/test/github/cisagov/hash-http-content/develop/badge.svg)](https://snyk.io/test/github/cisagov/hash-http-content)

This is a Python library to retrieve the contents of a given URL via HTTP (or
HTTPS) and hash the processed contents.

## Content processing ##

If an encoding is detected, this package will convert content into the UTF-8
encoding before proceeding.

Additional content processing is currently implemented for the following types
of content:

- HTML
- JSON

### HTML ###

HTML content is processed by leveraging the
[pyppeteer](https://github.com/pyppeteer/pyppeteer) package to execute any
JavaScript on a retrieved page. The result is then parsed by
[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) to reduce the
content to the human visible portions of a page.

### JSON ###

JSON content is processed by using the
[`json` library](https://docs.python.org/3/library/json.html) that is part of
the Python standard library. It is read in and then output in a deterministic
manner to adjust for any styling differences between content.

## Contributing ##

We welcome contributions!  Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for
details.

## License ##

This project is in the worldwide [public domain](LICENSE).

This project is in the public domain within the United States, and
copyright and related rights in the work worldwide are waived through
the [CC0 1.0 Universal public domain
dedication](https://creativecommons.org/publicdomain/zero/1.0/).

All contributions to this project will be released under the CC0
dedication. By submitting a pull request, you are agreeing to comply
with this waiver of copyright interest.
