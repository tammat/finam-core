from marketcore_os.repositories.capital_manager import CapitalManagerRepository
from marketcore_os.viewmodels.capital_manager import CapitalManagerViewModel


class CapitalManagerService:
    def __init__(self) -> None:
        self.repo = CapitalManagerRepository()

    def get_workspace_model(self) -> CapitalManagerViewModel:
        return CapitalManagerViewModel(**self.repo.load())
