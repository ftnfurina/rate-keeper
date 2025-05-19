from datetime import datetime, timezone
from typing import Dict

import requests
from requests import Response

from rate_keeper import RateKeeper


# UTC timestamp clock
def timestamp_clock():
    return datetime.now(timezone.utc).timestamp()


rate_keeper = RateKeeper(limit=5000, period=3600, clock=timestamp_clock)


@rate_keeper.decorator
def fetch(
    method: str, url: str, headers: Dict[str, str] = {}, params: Dict[str, str] = {}
) -> Response:
    # https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api#checking-the-status-of-your-rate-limit
    response = requests.request(method, url, headers=headers, params=params)

    headers_map = {
        "x-ratelimit-limit": lambda x: setattr(rate_keeper, "limit", int(x)),
        "x-ratelimit-used": lambda x: setattr(rate_keeper, "used", int(x)),
        "x-ratelimit-reset": lambda x: setattr(rate_keeper, "reset", float(x)),
    }

    for key, value in response.headers.items():
        lower_key = key.lower()
        if lower_key in headers_map:
            headers_map[lower_key](value)

    return response


def create_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Python requests GitHub API",
        "Authorization": f"token {token}",
    }


print(rate_keeper, f"{rate_keeper.recommend_delay:.2f}")
response = fetch("GET", "https://api.github.com/user", create_headers("github_token"))
print(response.json())
print(rate_keeper, f"{rate_keeper.recommend_delay:.2f}")
