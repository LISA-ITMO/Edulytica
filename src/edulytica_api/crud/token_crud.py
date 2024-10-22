from src.edulytica_api.crud.factory import BaseCrudFactory
from src.edulytica_api.models.models import Token
from src.edulytica_api.schemas.auth import TokenUpdate, TokenCreate, TokenGet


class TokenCrud(

    BaseCrudFactory(
        model=Token,
        update_schema=TokenUpdate,
        create_schema=TokenCreate,
        get_schema=TokenGet,
    )
):
    pass