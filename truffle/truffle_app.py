import inspect
import logging
import os
import typing
from concurrent import futures
from dataclasses import dataclass

import grpc
from google.protobuf import (
    descriptor_pool,
)
from google.protobuf.descriptor import (
    Descriptor,
    FieldDescriptor,
    MethodDescriptor,
)
from grpc_reflection.v1alpha import reflection

# from .client import TruffleReturnType, TruffleFile, TruffleImage

APP_SOCK = (
    os.getenv("TRUFFLE_APP_SOCKET")
    if os.getenv("TRUFFLE_APP_SOCKET") is not None
    else "unix:///tmp/truffle_app.sock"
)
SDK_SOCK = (
    os.getenv("TRUFFLE_SDK_SOCKET")
    if os.getenv("TRUFFLE_SDK_SOCKET") is not None
    else "unix:///tmp/truffle_sdk.sock"
)
log = logging.getLogger(__name__)


@dataclass(kw_only=True)
class AppMetadata:
    """The information about your app"""

    # User Facing information
    name: str  # user friendly name ex. "My Cool App"
    description: str  # what does your app do? ex. "My Cool App is a tool that helps you write haikus"
    icon: str = "icon.png"  # the icon for your app

    def __post_init__(self):
        if not self.validate():
            raise ValueError("Invalid AppMetadata")

    def validate(
        self,
    ) -> bool:  # todo: make it raise value error specific to what's wrong
        if self.name == "":
            return False
        if self.description == "":
            return False
        return True


def is_numeric_field(field: FieldDescriptor):
    numeric_types = [
        FieldDescriptor.TYPE_DOUBLE,
        FieldDescriptor.TYPE_FLOAT,
        FieldDescriptor.TYPE_INT32,
        FieldDescriptor.TYPE_INT64,
        FieldDescriptor.TYPE_UINT32,
        FieldDescriptor.TYPE_UINT64,
        FieldDescriptor.TYPE_SINT32,
        FieldDescriptor.TYPE_SINT64,
        FieldDescriptor.TYPE_FIXED32,
        FieldDescriptor.TYPE_FIXED64,
        FieldDescriptor.TYPE_SFIXED32,
        FieldDescriptor.TYPE_SFIXED64,
    ]
    return field.type in numeric_types


def is_float_field(field: FieldDescriptor):
    return field.type in [FieldDescriptor.TYPE_DOUBLE, FieldDescriptor.TYPE_FLOAT]


# yeah im just having fun at this point
def get_get_metadata(md: AppMetadata):
    def TruffleAppMetadata(self) -> dict[str, str]:
        return {
            "name": md.name,
            "description": md.description,
            "icon": md.icon,
        }

    TruffleAppMetadata.__truffle_tool__ = True
    TruffleAppMetadata.__truffle_description__ = "Returns the metadata for the app"
    TruffleAppMetadata.__truffle_icon__ = None
    TruffleAppMetadata.__truffle_args__ = None
    return TruffleAppMetadata


def get_non_function_members(obj):
    pr = {}
    for name in dir(obj):
        value = getattr(obj, name)
        if not name.startswith("__") and not inspect.ismethod(value):
            pr[name] = value
    return pr


def get_function_members(obj):
    pr = {}
    for name in dir(obj):
        value = getattr(obj, name)
        if not name.startswith("__") and inspect.ismethod(value):
            pr[name] = value
    return pr


def get_members(class_obj):
    return dict(
        (name, getattr(class_obj, name))
        for name in dir(class_obj)
        if not name.startswith("__")
    )


@dataclass
class ToolMethod:
    func: typing.Callable
    method: MethodDescriptor = None
    input_type: Descriptor = None
    output_type: Descriptor = None
    input_class: typing.Type = None
    output_class: typing.Type = None
    wrapper: typing.Callable = None


def debug_stub(*args):
    log.debug("reached internal SDK codepath")


def create_tool_method(func, class_obj) -> ToolMethod:
    """
    Generate the type information typically extracted from the .proto file for a service method.
    """
    pool = descriptor_pool.Default()
    method = ToolMethod(func=func)

    method.input_type, method.output_type = debug_stub(
        func, package=class_obj.__class__.__name__, descriptor_pool=pool
    )
    method.input_class = debug_stub(method.input_type)
    method.output_class = debug_stub(method.output_type)

    return method


class TruffleApp:
    def __init__(self, class_obj):
        """
        Sacrifice a class instance into the abyssal depths in exchange for
        a gRPC server that provides that class as a service w/ reflection!
        """
        self.metadata: AppMetadata = class_obj.metadata
        self.instance_of_class = class_obj
        self.tool_funcs = {}
        self.tool_funcs["TruffleAppMetadata"] = get_get_metadata(self.metadata)

        self.grpc_service_methods = {}

    def launch(self, socket_path: str = APP_SOCK):
        """
        Spin up a gRPC server, register our generated service and launch the server.
        """

        class AppService(object):
            def __init__(self, tool_methods, desc):
                """Yet Another wrapper which appears to exist to make the RPC server happy."""
                super().__init__()
                self.descriptor = desc
                self.tool_methods = tool_methods

            def __getattribute__(self, name: str) -> typing.Any:
                if name != "tool_methods":
                    if name in self.tool_methods:
                        return self.tool_methods[name].wrapper
                return super().__getattribute__(name)

        if os.path.exists(socket_path):
            os.unlink(socket_path)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
        self._service.registration_function(
            AppService(
                self.grpc_service_methods,
                self._service.descriptor,
            ),
            server,
        )
        service_names = (
            self._service.descriptor.full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, server)
        server.add_insecure_port(socket_path)
        log.info(f"Server listening on {socket_path}")
        print(f"Server listening on {socket_path}")
        server.start()
        server.wait_for_termination()
