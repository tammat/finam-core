class FinamRestClient:

    def __init__(self, token_manager):
        self.token_manager = token_manager

    def get(self, path):
        token = self.token_manager.get_token()
        print("REST request:", path)
        print("JWT head:", token[:20])
        return {}