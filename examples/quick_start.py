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
