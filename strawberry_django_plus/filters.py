from typing import Callable, Optional, Sequence, Type, TypeVar, cast

from django.db.models.base import Model
from strawberry.arguments import is_unset
from strawberry.field import StrawberryField
from strawberry.schema_directive import StrawberrySchemaDirective
from strawberry.utils.typing import __dataclass_transform__
from strawberry_django import filters as _filters
from strawberry_django import utils
from strawberry_django.fields.field import field as _field

from .field import field
from .relay import GlobalID, connection, node
from .type import input

_T = TypeVar("_T")


def _build_filter_kwargs(filters):
    filter_kwargs = {}
    filter_methods = []
    django_model = cast(Type[Model], utils.get_django_model(filters))

    for f in utils.fields(filters):
        field_name = f.name
        field_value = getattr(filters, field_name)
        if isinstance(field_value, GlobalID):
            field_value = field_value.node_id
        elif is_unset(field_value):
            continue

        if field_name in _filters.lookup_name_conversion_map:
            field_name = _filters.lookup_name_conversion_map[field_name]

        filter_method = getattr(filters, f"filter_{field_name}", None)
        if filter_method:
            filter_methods.append(filter_method)
            continue

        if django_model and field_name not in django_model._meta._forward_fields_map:  # type:ignore
            continue

        if utils.is_strawberry_type(field_value):
            subfield_filter_kwargs, subfield_filter_methods = _build_filter_kwargs(field_value)
            for subfield_name, subfield_value in subfield_filter_kwargs.items():
                filter_kwargs[f"{field_name}__{subfield_name}"] = subfield_value

            filter_methods.extend(subfield_filter_methods)
        else:
            filter_kwargs[field_name] = field_value

    return filter_kwargs, filter_methods


# Replace build_filter_kwargs by our implementation that can handle GlobalID
_filters.build_filter_kwargs = _build_filter_kwargs


@__dataclass_transform__(
    order_default=True,
    field_descriptors=(StrawberryField, field, _field, node, connection),
)
def filter(  # noqa:A001
    model: Type[Model],
    *,
    name: str = None,
    description: str = None,
    directives: Optional[Sequence[StrawberrySchemaDirective]] = (),
    lookups: bool = False,
) -> Callable[[_T], _T]:
    return input(
        model,
        name=name,
        description=description,
        directives=directives,
        is_filter="lookups" if lookups else True,
        partial=True,
    )