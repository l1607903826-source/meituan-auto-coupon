"""One coupon request; log only a fixed status and coupon count.

The endpoint and response codes are unverified assumptions from a public project.
No third-party Python packages, notifications, retries, or account data files.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from urllib import error, request


API_URL = "https://media.meituan.com/fulishemini/couponActivity/sendCouponWork"
MAX_RESPONSE_BYTES = 1_048_576
EXIT_CODES = {
    "success": 0,
    "already_received": 0,
    "no_token": 2,
    "empty": 3,
    "auth_failed": 4,
    "failed": 5,
    "error": 6,
}
MESSAGES = {
    "success": "The API returned coupons; check them in Meituan.",
    "already_received": "The API reports coupons were already received.",
    "no_token": "MEITUAN_TOKEN is missing or blank.",
    "empty": "No coupons returned; this run did not claim a coupon.",
    "auth_failed": "Authorization failed; update MEITUAN_TOKEN.",
    "failed": "The API rejected the request.",
    "error": "Request, response, or local output could not be processed.",
}


@dataclass(frozen=True)
class Result:
    status: str
    coupon_count: int = 0

    @property
    def exit_code(self):
        return EXIT_CODES[self.status]


class NoRedirect(request.HTTPRedirectHandler):
    """Keep the authorization payload on the one configured endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post_payload(payload):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "personal-coupon-action/1.0",
        },
        method="POST",
    )
    opener = request.build_opener(NoRedirect())
    with opener.open(req, timeout=20) as response:
        if response.status != 200:
            raise ValueError("Unexpected HTTP status")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("Response too large")
    return json.loads(raw.decode("utf-8"))


def interpret_response(response):
    if not isinstance(response, dict):
        return Result("error")
    code = response.get("code")
    if type(code) is not int:
        return Result("error")
    if code == 401:
        return Result("auth_failed")
    if code == 1014:
        return Result("already_received")
    if code != 200:
        return Result("failed")
    data = response.get("data")
    if not isinstance(data, dict):
        return Result("error")
    coupons = data.get("couponList", [])
    if not isinstance(coupons, list) or any(
        not isinstance(coupon, dict) for coupon in coupons
    ):
        return Result("error")
    return Result("success", len(coupons)) if coupons else Result("empty")


def claim(token, transport=None):
    token = token.strip()
    if not token:
        return Result("no_token")
    if transport is None:
        transport = post_payload
    try:
        response = transport({"token": token, "aiScene": "", "version": 2})
        return interpret_response(response)
    except error.HTTPError as exc:
        return Result("auth_failed" if exc.code == 401 else "failed")
    except (error.URLError, OSError, TimeoutError, ValueError, TypeError):
        # Exception strings and server messages may contain account data.
        return Result("error")


def summary_line(result):
    return (
        f"status={result.status}; coupon_count={result.coupon_count}; "
        f"{MESSAGES[result.status]}"
    )


def main():
    result = claim(os.environ.get("MEITUAN_TOKEN", ""))
    line = summary_line(result)
    print(line)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with Path(summary_path).open("a", encoding="utf-8") as output:
                output.write(f"### Meituan coupon result\n\n{line}\n")
        except OSError:
            print("status=error; could not write the fixed step summary.")
            return EXIT_CODES["error"]
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
