ASSET_METADATA = {
    "NGH6@RTSX": {
        "asset_class": "FUTURES",
        "point_value": 1.0,
        "margin_rate": 0.1,
    },
    # future instruments will be added here
}


def get_asset_metadata(symbol: str):
    return ASSET_METADATA.get(
        symbol,
        {
            "asset_class": "UNKNOWN",
            "point_value": 1.0,
            "margin_rate": 0.0,
        },
    )