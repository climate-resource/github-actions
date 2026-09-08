"""Send the published commit to a Flux generic-hmac Receiver."""

import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request


def notify(url, token, sha):
    if not url and not token:
        print("::notice::Flux receiver secrets are absent. Flux will poll instead.")
        return 0
    if not url or not token:
        print("::error::Set both FLUX_RECEIVER_URL and FLUX_RECEIVER_TOKEN.")
        return 1
    if not url.startswith("https://") or not sha:
        print("::error::Flux notification requires an HTTPS receiver URL and a commit SHA.")
        return 1
    body = json.dumps({"sha": sha}, separators=(",", ":")).encode()
    signature = hmac.new(token.encode(), body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "X-Signature": f"sha256={signature}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30):
            pass
    except (urllib.error.URLError, TimeoutError):
        print("::error::Flux notification failed. Check Receiver readiness and secret configuration.")
        return 1
    print("Flux notified of the published image.")
    return 0


if __name__ == "__main__":
    sys.exit(notify(os.getenv("FLUX_RECEIVER_URL", ""), os.getenv("FLUX_RECEIVER_TOKEN", ""), os.getenv("BUILD_SHA", "")))
