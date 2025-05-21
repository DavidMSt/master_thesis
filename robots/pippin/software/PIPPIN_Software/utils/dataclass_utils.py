import copy
import dataclasses
from enum import IntEnum

import graphviz
from utils.time import performance_analyzer
# Cache for frozen dataclass definitions
from dataclasses import fields, make_dataclass, is_dataclass, field
from typing import Any, Dict, Tuple, Type
from itertools import zip_longest
from typing import TypeVar, Type, Optional, get_type_hints, Mapping, Any, Collection, MutableMapping

from dacite.cache import cache
from dacite.config import Config
from dacite.data import Data
from dacite.dataclasses import (
    get_default_value_for_field,
    DefaultValueNotFoundError,
    get_fields,
    is_frozen,
)
from dacite.exceptions import (
    ForwardReferenceError,
    WrongTypeError,
    DaciteError,
    UnionMatchError,
    MissingValueError,
    DaciteFieldError,
    UnexpectedDataError,
    StrictUnionMatchError,
)
from dacite.types import (
    is_instance,
    is_generic_collection,
    is_union,
    extract_generic,
    is_optional,
    extract_origin_collection,
    is_init_var,
    extract_init_var,
    is_subclass,
)

T = TypeVar("T")


def from_dict(data_class: Type[T], data: Data, config: Optional[Config] = None) -> T:
    """Create a data class instance from a dictionary.

    :param data_class: a data class type
    :param data: a dictionary of a input data
    :param config: a configuration of the creation process
    :return: an instance of a data class
    """
    init_values: MutableMapping[str, Any] = {}
    post_init_values: MutableMapping[str, Any] = {}
    config = config or Config()
    try:
        data_class_hints = cache(get_type_hints)(data_class, localns=config.hashable_forward_references)
    except NameError as error:
        raise ForwardReferenceError(str(error))
    data_class_fields = cache(get_fields)(data_class)
    if config.strict:
        extra_fields = set(data.keys()) - {f.name for f in data_class_fields}
        if extra_fields:
            raise UnexpectedDataError(keys=extra_fields)
    for field in data_class_fields:
        field_type = data_class_hints[field.name]
        if field.name in data:
            try:
                field_data = data[field.name]
                value = _build_value(type_=field_type, data=field_data, config=config)
            except DaciteFieldError as error:
                error.update_path(field.name)
                raise
            if config.check_types and not is_instance(value, field_type):
                raise WrongTypeError(field_path=field.name, field_type=field_type, value=value)
        else:
            try:
                value = get_default_value_for_field(field, field_type)
            except DefaultValueNotFoundError:
                if not field.init:
                    continue
                raise MissingValueError(field.name)
        if field.init:
            init_values[field.name] = value
        elif not is_frozen(data_class):
            post_init_values[field.name] = value
    instance = data_class(**init_values)
    for key, value in post_init_values.items():
        setattr(instance, key, value)
    return instance


def _build_value(type_: Type, data: Any, config: Config) -> Any:
    if is_init_var(type_):
        type_ = extract_init_var(type_)
    if type_ in config.type_hooks:
        data = config.type_hooks[type_](data)
    if is_optional(type_) and data is None:
        return data
    if is_union(type_):
        data = _build_value_for_union(union=type_, data=data, config=config)
    elif is_generic_collection(type_):
        data = _build_value_for_collection(collection=type_, data=data, config=config)
    elif cache(is_dataclass)(type_) and isinstance(data, Mapping):
        data = from_dict(data_class=type_, data=data, config=config)
    elif issubclass(type_, IntEnum):  # Handle IntEnum explicitly
        if isinstance(data, int):
            return type_(data)  # Convert int to corresponding IntEnum value
        else:
            raise WrongTypeError(field_type=type_, value=data)
    for cast_type in config.cast:
        if is_subclass(type_, cast_type):
            if is_generic_collection(type_):
                data = extract_origin_collection(type_)(data)
            else:
                data = type_(data)
            break
    return data

def _build_value_for_union(union: Type, data: Any, config: Config) -> Any:
    types = extract_generic(union)
    if is_optional(union) and len(types) == 2:
        return _build_value(type_=types[0], data=data, config=config)
    union_matches = {}
    for inner_type in types:
        try:
            # noinspection PyBroadException
            try:
                value = _build_value(type_=inner_type, data=data, config=config)
            except Exception:  # pylint: disable=broad-except
                continue
            if is_instance(value, inner_type):
                if config.strict_unions_match:
                    union_matches[inner_type] = value
                else:
                    return value
        except DaciteError:
            pass
    if config.strict_unions_match:
        if len(union_matches) > 1:
            raise StrictUnionMatchError(union_matches)
        return union_matches.popitem()[1]
    if not config.check_types:
        return data
    raise UnionMatchError(field_type=union, value=data)


def _build_value_for_collection(collection: Type, data: Any, config: Config) -> Any:
    data_type = data.__class__
    if isinstance(data, Mapping) and is_subclass(collection, Mapping):
        item_type = extract_generic(collection, defaults=(Any, Any))[1]
        return data_type((key, _build_value(type_=item_type, data=value, config=config)) for key, value in data.items())
    elif isinstance(data, tuple) and is_subclass(collection, tuple):
        if not data:
            return data_type()
        types = extract_generic(collection)
        if len(types) == 2 and types[1] == Ellipsis:
            return data_type(_build_value(type_=types[0], data=item, config=config) for item in data)
        return data_type(
            _build_value(type_=type_, data=item, config=config) for item, type_ in zip_longest(data, types)
        )
    elif isinstance(data, Collection) and is_subclass(collection, Collection):
        item_type = extract_generic(collection, defaults=(Any,))[0]
        return data_type(_build_value(type_=item_type, data=item, config=config) for item in data)
    return data


_frozen_dataclass_cache: Dict[Tuple[type, Tuple[str, type]], type] = {}


def freeze_dataclass_instance(instance: Any) -> Any:
    """
    Takes a dataclass instance and converts it and all its nested dataclasses into immutable frozen versions.
    Cached frozen versions are used to optimize repeated conversions.

    Args:
        instance (Any): The dataclass instance to freeze.

    Returns:
        Any: A frozen copy of the dataclass instance.
    """
    if not is_dataclass(instance):
        raise ValueError("The input must be an instance of a dataclass.")

    def get_frozen_dataclass_type(cls: type) -> type:
        """Retrieve or create a frozen version of the dataclass."""
        # noinspection PyDataclass
        cls_fields = tuple((f.name, f.type) for f in fields(cls))
        cache_key = (cls, cls_fields)

        if cache_key not in _frozen_dataclass_cache:
            # noinspection PyArgumentList,PyDataclass
            frozen_cls = make_dataclass(
                cls.__name__ + "Frozen",
                [
                    (
                        f.name,
                        f.type,
                        field(
                            default=f.default
                            if f.default is not dataclasses.MISSING
                            else dataclasses.MISSING,
                            default_factory=f.default_factory
                            if f.default_factory is not dataclasses.MISSING
                            else dataclasses.MISSING,
                        ),
                    )
                    for f in fields(cls)
                ],
                frozen=True
            )
            _frozen_dataclass_cache[cache_key] = frozen_cls # type: ignore
        return _frozen_dataclass_cache[cache_key] # type: ignore

    def freeze_instance(dataclass_instance: Any) -> Any:
        """Recursively convert a dataclass instance into its frozen version."""
        cls = type(dataclass_instance)
        frozen_cls = get_frozen_dataclass_type(cls)

        frozen_kwargs = {}
        for f in fields(cls):
            value = getattr(dataclass_instance, f.name)
            if is_dataclass(value):
                frozen_kwargs[f.name] = freeze_instance(value)
            else:
                frozen_kwargs[f.name] = copy.deepcopy(value)

        return frozen_cls(**frozen_kwargs)

    return freeze_instance(instance)

def analyze_dataclass(
        dataclass_type: Type[Any],
        print_to_terminal: bool = False,
        print_to_file: bool = True,
        generate_figure: bool = False,
):
    """
    Generates diagnostics for a dataclass, including its fields and nested structures.
    Ensures unique nodes for fields with the same name and prevents parents from linking to grandchildren.

    :param dataclass_type: The dataclass type to process.
    :param print_to_terminal: If True, prints the field paths to the terminal.
    :param print_to_file: If True, writes the field paths to a .txt file named after the dataclass.
    :param generate_figure: If True, generates a tree diagram named after the dataclass.
    """
    if not is_dataclass(dataclass_type):
        raise ValueError("The provided type is not a dataclass.")

    # Define color mapping for types
    type_colors = {
        "dataclass": "lightblue",
        "float": "lightgreen",
        "int": "lightcoral",
        "str": "wheat",
        "List": "yellow",
        "Dict": "pink",
        "Optional": "gray",
    }

    def get_color(field_type):
        """Get the color for a field type."""
        if hasattr(field_type, "__origin__"):  # Handle typing constructs (e.g., List, Dict, Optional)
            origin = field_type.__origin__.__name__
            return type_colors.get(origin, "white")
        if is_dataclass(field_type):  # Handle dataclasses
            return type_colors["dataclass"]
        return type_colors.get(field_type.__name__, "white")  # Default to white if no match

    def get_field_paths_and_structure(data_type, prefix=""):
        """Recursively extracts fields and nested dataclasses."""
        paths = []
        structure = []
        for field in fields(data_type):
            field_name = field.name
            field_type = field.type
            full_path = f"{prefix}{field_name}"

            paths.append(full_path)  # Add current field's path
            structure.append((prefix, field_name, field_type, is_dataclass(field_type)))

            # If the field type is another dataclass, process it recursively
            if is_dataclass(field_type):
                nested_paths, nested_structure = get_field_paths_and_structure(field_type, prefix=f"{full_path}.")
                paths.extend(nested_paths)
                structure.extend(nested_structure)
        return paths, structure

    # Generate field paths and structure
    all_paths, structure = get_field_paths_and_structure(dataclass_type)

    # Write the paths to the output file if enabled
    dataclass_name = dataclass_type.__name__
    if print_to_file:
        txt_file_name = f"{dataclass_name}.txt"
        with open(txt_file_name, "w") as file:
            file.write(f"Fields and Paths for Dataclass: {dataclass_name}\n")
            for path in all_paths:
                file.write(f"{path}\n")

    # Optionally print paths to terminal
    if print_to_terminal:
        print(f"Fields and Paths for Dataclass: {dataclass_name}")
        for path in all_paths:
            print(path)

    # Optionally generate a tree diagram
    if generate_figure:
        graph = graphviz.Digraph(format="png")
        graph.attr(rankdir="TB")  # Top-to-Bottom layout
        graph.attr("node", shape="box")

        # Add the root node for the dataclass
        root_name = dataclass_type.__name__
        graph.node(root_name, f"{root_name} (dataclass)", style="filled", fillcolor=type_colors["dataclass"])

        # Recursive function to add nodes and edges
        def add_to_graph(parent, current_prefix, structure):
            for prefix, field_name, field_type, is_nested in structure:
                # Only connect immediate children to the current parent
                if prefix.rstrip(".") == current_prefix.rstrip("."):
                    # Create a globally unique node ID using the full path
                    node_id = f"{prefix}{field_name}".replace(".", "_")
                    node_label = f"{field_name} ({field_type.__name__})" if not is_nested else field_name
                    color = get_color(field_type)

                    # Add the node to the graph
                    graph.node(node_id, node_label, style="filled", fillcolor=color)
                    graph.edge(parent, node_id)

                    # Recursively add nested dataclass children
                    if is_nested:
                        nested_structure = [
                            item for item in structure if item[0].startswith(f"{prefix}{field_name}.")
                        ]
                        add_to_graph(node_id, f"{prefix}{field_name}.", nested_structure)

        # Start adding nodes from the root
        add_to_graph(root_name, "", structure)

        # Render the figure with the name of the dataclass
        graph.render(dataclass_name, cleanup=True)