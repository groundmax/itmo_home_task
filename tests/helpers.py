
import typing as tp

from requestor.db.models import Base

DBObjectCreator = tp.Callable[[Base], None]
