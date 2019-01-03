from sanic.blueprints import Blueprint
from sanic.response import json
from inspect import isawaitable
from functools import wraps

from itertools import repeat
from sanic.views import CompositionView

from sanic_openapi.doc import route_specs, RouteSpec, serialize_schema, definitions

blueprint = Blueprint("testapi", url_prefix="testapi")

_spec = {}


def builder(**kw):
    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):

            resp = ""
            return resp

        return decorated_function

    return decorator


@blueprint.listener("before_server_start")
def build_spec(app, loop):
    for blueprint in app.blueprints.values():
        if hasattr(blueprint, "routes"):
            for route in blueprint.routes:
                route_spec = route_specs[route.handler]

    for uri, route in app.router.routes_all.items():
        if (
            uri.startswith("/swagger")
            or uri.startswith("/openapi")
            or "<file_uri" in uri
        ):
            # TODO: add static flag in sanic routes
            continue

        # Build list of methods and their handler functions
        handler_type = type(route.handler)
        if handler_type is CompositionView:
            view = route.handler
            method_handlers = view.handlers.items()
        else:
            method_handlers = zip(route.methods, repeat(route.handler))

        for _method, _handler in method_handlers:

            route_spec = route_specs.get(_handler) or RouteSpec()
            route_parameters = []
            for parameter in route.parameters:
                route_parameters.append(
                    {
                        **serialize_schema(parameter.cast),
                        "required": True,
                        "in": "path",
                        "name": parameter.name,
                    }
                )
            for consumer in route_spec.consumes:
                spec = serialize_schema(consumer.field)
                if "properties" in spec:
                    for name, prop_spec in spec["properties"].items():
                        route_param = {
                            **prop_spec,
                            "required": consumer.required,
                            "in": consumer.location,
                            "name": name,
                        }
                else:
                    route_param = {
                        **spec,
                        "required": consumer.required,
                        "in": consumer.location,
                        "name": consumer.field.name
                        if hasattr(consumer.field, "name")
                        else "body",
                    }

                if "$ref" in route_param:
                    route_param["schema"] = {"$ref": route_param["$ref"]}
                    del route_param["$ref"]

                route_parameters.append(route_param)


@blueprint.route("/spec.json")
def spec(request):
    return json(_spec)
