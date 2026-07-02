from marketcore_os.repositories.portfolio import PortfolioRepository
from marketcore_os.viewmodels.portfolio import PortfolioViewModel

class PortfolioService:

    def __init__(self):
        self.repo=PortfolioRepository()

    def get_workspace_model(self):

        d=self.repo.load()

        return PortfolioViewModel(**d)
