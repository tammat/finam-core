import requests


class FinamRestClient:

    def __init__(self, token_manager):

        self.base_url = "https://api.finam.ru"
        self.token_manager = token_manager

    def get(self, path):

        token = self.token_manager.get_token()

        headers = {
            "Authorization": f"Bearer {token}"
        }

        r = requests.get(self.base_url + path, headers=headers)

        r.raise_for_status()

        return r.json()

    def post(self, path, payload):

        token = self.token_manager.get_token()

        headers = {
            "Authorization": f"Bearer {token}"
        }

        r = requests.post(
            self.base_url + path,
            json=payload,
            headers=headers
        )

        r.raise_for_status()

        return r.json()