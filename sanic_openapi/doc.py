from collections import defaultdict
from datetime import date, datetime
import yaml
from typing import List as ListTyping


class Field:
    def __init__(
        self, description=None, required=None, name=None, choices=None, example=None
    ):
        self.name = name
        self.description = description
        self.required = required
        self.choices = choices
        self.example = example

    def serialize(self):
        output = {}
        if self.name:
            output["name"] = self.name
        if self.description:
            output["description"] = self.description
        if self.required is not None:
            output["required"] = self.required
        if self.choices is not None:
            output["enum"] = self.choices
        if self.example is not None:
            output["example"] = self.example
        return output


class Integer(Field):
    def serialize(self):
        return {"type": "integer", "format": "int64", **super().serialize()}


class Float(Field):
    def serialize(self):
        return {"type": "number", "format": "double", **super().serialize()}


class String(Field):
    def serialize(self):
        return {"type": "string", **super().serialize()}


class Boolean(Field):
    def serialize(self):
        return {"type": "boolean", **super().serialize()}


class Tuple(Field):
    pass


class Date(Field):
    def serialize(self):
        return {"type": "string", "format": "date", **super().serialize()}


class DateTime(Field):
    def serialize(self):
        return {"type": "string", "format": "date-time", **super().serialize()}


class Dictionary(Field):
    def __init__(self, fields=None, **kwargs):
        self.fields = fields or {}
        super().__init__(**kwargs)

    def serialize(self):
        return {
            "type": "object",
            "properties": {
                key: serialize_schema(schema) for key, schema in self.fields.items()
            },
            **super().serialize(),
        }


class List(Field):
    def __init__(self, items=None, *args, **kwargs):
        self.items = items or []
        if type(self.items) is not list:
            self.items = [self.items]
        super().__init__(*args, **kwargs)

    def serialize(self):
        if len(self.items) > 1:
            items = Tuple(self.items).serialize()
        elif self.items:
            items = serialize_schema(self.items[0])
        else:
            items = []
        return {"type": "array", "items": items}


definitions = {}
# TODO
security_definitions = {}


class ParseClass:
    def __init__(self, cls, obj=None, name=None):
        self.cls = cls
        self.obj = obj
        self.name = name


def parse_yaml(classes: ListTyping[ParseClass]):
    # classes = (class, obj, name)
    for cls in classes:
        if cls.cls not in definitions:
            definition = {"type": "object", "required": [], "properties": {}}

            full_doc = cls.cls.__doc__

            yaml_start = full_doc.find("---")
            swag = yaml.safe_load(full_doc[yaml_start if yaml_start >= 0 else 0 :])

            if swag and "required" in swag and swag["required"]:
                definition["required"] = swag["required"]
            if swag and "properties" in swag and swag["properties"]:
                definition["properties"] = swag["properties"]

            if (
                hasattr(cls.cls, "__dataclass_fields__")
                and cls.cls.__dataclass_fields__
                and swag
                and "properties" in swag
            ):

                properties_class = set(list(cls.cls.__dataclass_fields__.keys()))
                properties_swag = set(list(definition["properties"].keys()))

                if properties_swag - properties_class:
                    raise ValueError(
                        f"There are more properties defined in the __doc__ of {cls.cls} then attributes it has: {properties_swag - properties_class}"
                    )
                if properties_class - properties_swag:
                    raise ValueError(
                        f"There are more properties defined in the attributes of {cls.cls} then in the __doc__ it has: {properties_class - properties_swag}"
                    )

                # check if reference in swag yaml and append them to definitions
                # then do a recursive function that parses yaml
                to_parse = []
                for k, v in swag["properties"].items():
                    if "ref" in v:
                        for j, w in cls.cls.__dataclass_fields__.items():
                            if v["ref"] == w.type.__name__:
                                parse = ParseClass(w.type, name=w.type.__name__)
                                to_parse.append(parse)
                                # to_inspect()
                        v["$ref"] = f"#/definitions/{v['ref']}"
                        del v["ref"]
                parse_yaml(to_parse)

        if cls.obj:
            definitions[cls.cls] = (cls.obj, definition)
        elif cls.name:
            definitions[cls.cls] = (cls.name, definition)
        else:
            raise Exception("no obj nor name defined")


class Object(Field):
    def __init__(self, cls, *args, object_name=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.cls = cls
        self.object_name = object_name or cls.__name__

        if self.cls not in definitions:
            definition = self.definition

            if hasattr(self.cls, "__doc__") and self.cls.__doc__:
                cls = ParseClass(cls=cls, obj=self)
                parse_yaml([cls])
            elif "properties" in definition and isinstance(
                definition["properties"], dict
            ):
                # remove empty dict
                definition["properties"] = {
                    k: v for k, v in definition["properties"].items() if v
                }
                definitions[self.cls] = (self, definition)
                # here we yaml parse
                # @dataclass(config=GlobalConfig)
                # class A(DataClass):
                #     """
                #     some doc
                #     ---
                #     required:
                #     - name
                #     - a
                #     properties:
                #         attr1:
                #             description: Cat's name
                #             type: string
                #             example: Sylvester
                #     """
                #
                #     attr1: str
                #
                #     def aa(self):
                #         pass

                # definition = self.definition
                # full_doc = self.cls.__doc__
                #
                # yaml_start = full_doc.find("---")
                # swag = yaml.safe_load(full_doc[yaml_start if yaml_start >= 0 else 0 :])
                # if swag and "required" in swag and swag["required"]:
                #     definition["required"] = swag["required"]
                # if swag and "properties" in swag and swag["properties"]:
                #     definition["properties"] = swag["properties"]
                #
                # if (
                #     hasattr(self.cls, "__dataclass_fields__")
                #     and self.cls.__dataclass_fields__
                #     and swag
                #     and "properties" in swag
                # ):
                #
                #     properties_class = set(list(self.cls.__dataclass_fields__.keys()))
                #     properties_swag = set(list(definition["properties"].keys()))
                #
                #     if properties_swag - properties_class:
                #         raise ValueError(
                #             f"There are more properties defined in the __doc__ of {self.cls} then attributes it has: {properties_swag - properties_class}"
                #         )
                #     if properties_class - properties_swag:
                #         raise ValueError(
                #             f"There are more properties defined in the attributes of {self.cls} then in the __doc__ it has: {properties_class - properties_swag}"
                #         )
                #
                #     print("---" * 100)
                #
                #     # check if reference in swag yaml and append them to definitions
                #     for k, v in swag["properties"].items():
                #         if "ref" in v:
                #             # print(v)
                #             # # print(getattr(self.cls, v["ref"]))
                #             # print(dir(self.cls))
                #             # print(self.cls.__validate__)
                #             # print(self.cls.__dataclass_fields__)
                #             for j, w in self.cls.__dataclass_fields__.items():
                #                 # print(dir(w.type))
                #                 # print(w.type.__name__)
                #                 if v["ref"] == w.type.__name__:
                #                     print(w.type.__doc__)
                #             v["$ref"] = f"#/definitions/{v['ref']}"
                #             del v["ref"]

    @property
    def definition(self):
        return {
            "type": "object",
            "required": [
                attr
                for attr, schema in self.cls.__dict__.items()
                if hasattr(schema, "required") and schema.required
            ],
            "properties": {
                key: serialize_schema(schema)
                for key, schema in self.cls.__dict__.items()
                if not key.startswith("_")
            },
            **super().serialize(),
        }

    def serialize(self):
        return {
            "type": "object",
            "$ref": "#/definitions/{}".format(self.object_name),
            **super().serialize(),
        }


def serialize_schema(schema):
    schema_type = type(schema)

    # --------------------------------------------------------------- #
    # Class
    # --------------------------------------------------------------- #
    if schema_type is type:
        if issubclass(schema, Field):
            return schema().serialize()
        elif schema is dict:
            return Dictionary().serialize()
        elif schema is list:
            return List().serialize()
        elif schema is int:
            return Integer().serialize()
        elif schema is float:
            return Float().serialize()
        elif schema is str:
            return String().serialize()
        elif schema is bool:
            return Boolean().serialize()
        elif schema is date:
            return Date().serialize()
        elif schema is datetime:
            return DateTime().serialize()
        else:
            return Object(schema).serialize()

    # --------------------------------------------------------------- #
    # Object
    # --------------------------------------------------------------- #
    else:
        if issubclass(schema_type, Field):
            return schema.serialize()
        elif schema_type is dict:
            return Dictionary(schema).serialize()
        elif schema_type is list:
            return List(schema).serialize()

    return {}


# --------------------------------------------------------------- #
# Route Documenters
# --------------------------------------------------------------- #


class RouteSpec(object):
    consumes = None
    consumes_content_type = None
    produces = None
    produces_content_type = None
    summary = None
    description = None
    operation = None
    blueprint = None
    tags = None
    exclude = None
    responses = None
    security = None

    def __init__(self):
        self.tags = []
        self.consumes = []
        self.responses = {}
        self.security = []
        super().__init__()


class RouteField(object):
    field = None
    location = None
    required = None

    def __init__(self, field, location=None, required=False):
        self.field = field
        self.location = location
        self.required = required


route_specs = defaultdict(RouteSpec)


def exclude(boolean):
    def inner(func):
        route_specs[func].exclude = boolean
        return func

    return inner


def summary(text):
    def inner(func):
        route_specs[func].summary = text
        return func

    return inner


def description(text):
    def inner(func):
        route_specs[func].description = text
        return func

    return inner


def consumes(*args, content_type=None, location="query", required=False):
    def inner(func):
        if args:
            for arg in args:
                field = RouteField(arg, location, required)
                route_specs[func].consumes.append(field)
                route_specs[func].consumes_content_type = content_type
        return func

    return inner


def produces(*args, content_type=None):
    def inner(func):
        if args:
            field = RouteField(args[0])
            route_specs[func].produces = field
            route_specs[func].produces_content_type = content_type
        return func

    return inner


def tag(name):
    def inner(func):
        route_specs[func].tags.append(name)
        return func

    return inner


def security(*args):
    def inner(func):
        if args:
            for arg in args:
                route_specs[func].security.append(arg)
        return func

    return inner


def response(code, description=None, examples=None):
    def inner(func):
        route_specs[func].responses[code] = {
            "description": description,
            "example": examples,
        }
        return func

    return inner
