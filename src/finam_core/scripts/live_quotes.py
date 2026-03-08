import os
from finam_core.ingestion.live_market_feed import LiveMarketFeed
def main():
    feed = LiveMarketFeed(
        host=os.getenv("FINAM_GRPC_HOST") or os.getenv("FINAM_API_HOST"),
        jwt=os.getenv("FINAM_JWT") or os.getenv("FINAM_TOKEN") or os.getenv("JWT"),
    )
 #   feed.subscribe_quotes(["NGH6@RTSX", "GAZP@MISX", "SBER@MISX"])
    feed.subscribe_trades(["SBER@MISX"])
if __name__ == "__main__":
    main()