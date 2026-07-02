from marketcore_os.repositories.intraday import IntradayRepository
from marketcore_os.viewmodels.intraday import IntradayViewModel

class IntradayService:

    def __init__(self):
        self.repo=IntradayRepository()

    def get_workspace_model(self):

        return IntradayViewModel(
            **self.repo.load()
        )
