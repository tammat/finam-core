from marketcore_os.repositories.daily import DailyCenterRepository
from marketcore_os.viewmodels.daily import DailyCenterViewModel


class DailyCenterService:
    def __init__(self) -> None:
        self.repo = DailyCenterRepository()

    def get_workspace_model(self) -> DailyCenterViewModel:
        return DailyCenterViewModel(**self.repo.load())
