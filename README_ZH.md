![badge-collection](https://socialify.git.ci/ftnfurina/rate-keeper/image?font=Bitter&forks=1&issues=1&language=1&name=1&owner=1&pattern=Floating+Cogs&pulls=1&stargazers=1&theme=Auto)

<div align="center">
  <h1>Rate Keeper</h1>
  <p>
    <a href="https://github.com/ftnfurina/rate-keeper/blob/main/README_ZH.md">中文</a> |
    <a href="https://github.com/ftnfurina/rate-keeper/blob/main/README.md">English</a>
  </p>
</div>

**频率守护器：用于限制函数调用频率。它能确保您的函数在限制范围内均匀调用，而不是在短时间内被密集调用。此外，它还能根据剩余调用次数和时间动态调整调用频率。**

## 安装

```shell
pip install rate-keeper
```

## 快速开始

```python
from rate_keeper import RateKeeper

if __name__ == "__main__":
    rate_keeper = RateKeeper(limit=3, period=1)

    @rate_keeper.decorator
    def request(url: str) -> str:
        print(f"Requesting {url}, {rate_keeper}, {rate_keeper.recommend_delay:.2f}")

    count = 0
    while count < 6:
        request(f"https://www.example.com/{count}")
        count += 1

# Output:
# Requesting https://www.example.com/0, RateKeeper(limit=3, period=1, used=1, reset=55981.89), 0.50
# Requesting https://www.example.com/1, RateKeeper(limit=3, period=1, used=2, reset=55981.89), 0.50
# Requesting https://www.example.com/2, RateKeeper(limit=3, period=1, used=1, reset=55982.89), 0.50
# Requesting https://www.example.com/3, RateKeeper(limit=3, period=1, used=2, reset=55982.89), 0.50
# Requesting https://www.example.com/4, RateKeeper(limit=3, period=1, used=1, reset=55983.906), 0.50
# Requesting https://www.example.com/5, RateKeeper(limit=3, period=1, used=2, reset=55983.906), 0.50
```

## 动态调整

```python
from typing import Dict
import requests
from requests import Response
from datetime import datetime, timezone
from rate_keeper import RateKeeper

timestamp_clock = datetime.now(timezone.utc).timestamp
rate_keeper = RateKeeper(limit=5000, period=3600, clock=timestamp_clock)


@rate_keeper.decorator
def fetch(
    method: str, url: str, headers: Dict[str, str] = {}, params: Dict[str, str] = {}
) -> Response:
    # https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api#checking-the-status-of-your-rate-limit
    response = requests.request(method, url, headers=headers, params=params)

    headers_map = {
        "x-ratelimit-limit": rate_keeper.update_limit,
        "x-ratelimit-used": rate_keeper.update_used,
        "x-ratelimit-reset": rate_keeper.update_reset,
    }

    for key, value in response.headers.items():
        lower_key = key.lower()
        if lower_key in headers_map:
            headers_map[lower_key](int(value))

    return response


def create_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Follower Bot",
        "Authorization": f"token {token}",
    }


print(rate_keeper)
response = fetch("GET", "https://api.github.com/user", create_headers("github_token"))
print(response.json())
print(rate_keeper)

# Output:
# RateKeeper(limit=5000, period=3600, used=0, reset=1745863571.523727)
# {'message': 'Bad credentials', 'documentation_url': 'https://docs.github.com/rest', 'status': '401'}
# RateKeeper(limit=60, period=3600, used=7, reset=1745862671)
```