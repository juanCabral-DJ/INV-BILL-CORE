from app.base.crud_base import CRUDBase
from app.models.models import Categoria
from app.schemas.schemas import CategoriaCreate, CategoriaUpdate


class CategoriasService(CRUDBase[Categoria, CategoriaCreate, CategoriaUpdate]):
    pass


categorias_service = CategoriasService(model=Categoria)
