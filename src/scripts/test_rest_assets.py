import requests
from finam_core.auth.token_manager import FinamTokenManager


def main():

    tm = FinamTokenManager()
    token = tm.get_token()

    url = "https://tradeapi.finam.ru/api/v1/assets"

    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"}
    )

    print("status:", r.status_code)
    print(r.text[:500])


if __name__ == "__main__":
    main()