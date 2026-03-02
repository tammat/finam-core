import os
from ingestion.live_market_feed import LiveMarketFeed

def main():
    feed = LiveMarketFeed(
        host=os.getenv("FINAM_GRPC_HOST") or os.getenv("FINAM_API_HOST"),
        jwt=os.getenv("FINAM_JWT") or os.getenv("FINAM_TOKEN") or os.getenv("JWT"),
    )
    feed.subscribe_quotes(["GAZP@MISX", "SBER@MISX", "LKOH@MISX"])

if __name__ == "__main__":
    main()