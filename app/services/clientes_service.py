from app.base.crud_base import CRUDBase
from app.models.models import Cliente
from app.schemas.schemas import ClienteCreate, ClienteUpdate


class ClientesService(CRUDBase[Cliente, ClienteCreate, ClienteUpdate]):
    pass


clientes_service = ClientesService(model=Cliente)
