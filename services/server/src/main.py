import os
import sys

import logger
import server

SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "12345"))
STORAGE_PATH = os.environ["STORAGE_PATH"]

def main():
    logger.init()
    s = server.Server(SERVER_HOST, SERVER_PORT, STORAGE_PATH)
    try:
        s.run()
    except Exception as e:
        logger.error("server-run", logger.LogResult.fail, "err", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
