import logging

from rate_keeper import RateKeeper

# from rate_keeper import LOGGER_NAME

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(levelname)-6s : %(message)s"
)

logger = logging.getLogger(__name__)
rate_keeper = RateKeeper(limit=3, period=1)

# rate_keeper_logger = logging.getLogger(LOGGER_NAME)
# rate_keeper_logger.setLevel(logging.INFO)


@rate_keeper.decorator
def logging_msg(msg: str) -> None:
    logger.info(msg)


if __name__ == "__main__":
    [logging_msg(f"msg {i}") for i in range(10)]
