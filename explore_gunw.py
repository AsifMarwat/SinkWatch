"""
SinkWatch - Step 1: Peek inside one NISAR GUNW file WITHOUT downloading it.

What it does:
  - Logs in to NASA Earthdata (asks for username/password the first time,
    then remembers them in your .netrc file).
  - Opens the FIRST .h5 URL from urls.txt directly on NASA's server.
  - Prints the "table of contents" of the file: every layer, its shape and type.
  - Reads only a few kilobytes - nothing big is downloaded.

Setup (run once in your terminal):
  pip install earthaccess h5py fsspec aiohttp numpy

Usage:
  1. In ASF Vertex > Downloads, click "Copy URLs", paste into a file named
     urls.txt in the same folder as this script, and save.
  2. python explore_gunw.py
  3. Send the printed output (or explore_output.txt) back to Claude.
"""

import sys
import earthaccess
import h5py

URL_FILE = "urls.txt"
OUT_FILE = "explore_output.txt"


def load_h5_urls(path):
    with open(path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    h5_urls = [u for u in urls if u.lower().endswith(".h5")]
    if not h5_urls:
        sys.exit(f"No .h5 URLs found in {path}. Paste the URLs from 'Copy URLs' first.")
    return h5_urls


def main():
    urls = load_h5_urls(URL_FILE)
    print(f"Found {len(urls)} .h5 URLs. Exploring the first one:\n{urls[0]}\n")

    # Log in (first time: asks for Earthdata username/password and saves them)
    earthaccess.login(strategy="interactive", persist=True)
    fs = earthaccess.get_fsspec_https_session()

    lines = []

    def visitor(name, obj):
        if isinstance(obj, h5py.Dataset):
            lines.append(f"{name}  shape={obj.shape}  dtype={obj.dtype}")

    # Stream the file: only the small pieces we touch are fetched
    with fs.open(urls[0], "rb", block_size=4 * 1024 * 1024, cache_type="blockcache") as remote:
        with h5py.File(remote, "r") as h5:
            h5.visititems(visitor)

    text = "\n".join(lines)
    print(text)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\nSaved the list of {len(lines)} layers to {OUT_FILE}")


if __name__ == "__main__":
    main()
