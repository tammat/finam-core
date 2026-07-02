from marketcore_os.repositories.runtime import RuntimeCenterRepository
from marketcore_os.viewmodels.runtime import RuntimeCenterViewModel


class RuntimeCenterService:
    def __init__(self) -> None:
        self.repo = RuntimeCenterRepository()

    def get_workspace_model(self) -> RuntimeCenterViewModel:
        return RuntimeCenterViewModel(**self.repo.load())
