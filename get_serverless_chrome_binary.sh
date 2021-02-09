#!/usr/bin/env bash

set -o nounset
set -o errexit
set -o pipefail

function usage {
  echo "Usage:"
  echo "  ${0##*/} [options]"
  echo
  echo "Options:"
  echo "  -h, --help    Show the help message."
  echo "  -l, --latest  Pull down the latest release on GitHub."
  exit "$1"
}

# Defaults to a specific version for use in GitHub Actions
DOWNLOAD_URL="https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-57/stable-headless-chromium-amazonlinux-2.zip"
LOCAL_FILE="serverless-chrome.zip"
LOCAL_DIR="tests/files/"


# Get the URL of the latest stable release available
function get_latest_stable_url {
  releases_url="https://api.github.com/repos/adieuadieu/serverless-chrome/releases"
  # Get the URL for the latest release's assets
  latest_assets=$(curl -s "$releases_url" | jq -r '.[0].assets_url')
  # Download the zip for the stable branch
  DOWNLOAD_URL=$(curl -s "$latest_assets" | jq -r '.[] | select(.browser_download_url | contains("stable")) | .browser_download_url')
}

while (( "$#" ))
do
  case "$1" in
    -h|--help)
      usage 0
      ;;
    -l|--latest)
      get_latest_stable_url
      shift 1
      ;;
    -*)
      usage 1
      ;;
  esac
done

# Follow redirects and output as the specified file name
curl -L --output "$LOCAL_FILE" "$DOWNLOAD_URL"
# Extract the specified file to the specified directory and overwrite without
# prompting
unzip -o "$LOCAL_FILE" -d "$LOCAL_DIR"
