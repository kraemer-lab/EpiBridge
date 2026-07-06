import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

logger.info("Worker stub — awaiting implementation")


def main():
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
