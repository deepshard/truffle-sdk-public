import functools
import inspect
import logging
import os
import traceback
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
from google.protobuf.json_format import MessageToDict
from grpc_reflection.v1alpha import reflection

from .client import TruffleReturnType, TruffleFile, TruffleImage
from . import toproto

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
    icon: str  # the icon for your app

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


def create_tool_method(func, class_obj) -> ToolMethod:
    """
    Generate the type information typically extracted from the .proto file for a service method.
    """
    pool = descriptor_pool.Default()
    method = ToolMethod(func=func)

    method.input_type, method.output_type = toproto.func_to_proto(
        func, package=class_obj.__class__.__name__, descriptor_pool=pool
    )
    method.input_class = toproto.descriptor_to_message_class(method.input_type)
    method.output_class = toproto.descriptor_to_message_class(method.output_type)

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
        # find the methods marked for agentic use and store them
        for name, func in get_function_members(class_obj).items():
            if hasattr(func, "__truffle_tool__"):
                # Perhaps we instead yell at someone if they don't pass self instead
                if hasattr(func, "__self__"):
                    self.tool_funcs[name] = func.__func__
                else:
                    self.tool_funcs[name] = func

        # add get metadata tool
        self.tool_funcs["TruffleAppMetadata"] = get_get_metadata(self.metadata)
        # NOTE: What follows is my best explanation of how we approach
        # generating fully-fledged gRPC services starting from nothing but a
        # python function object in memory. You have been warned!!!

        ########## Part 1: Generate the contents which usually comes from the Service Descriptor ################
        # In order for the gRPC service to be discovered at runtime, it needs to also provide a Service Descriptor.
        # Instead of going the "blessed" route of having a proto and handing them off to a compiler, we hack up
        # what the compiler what generate from the type information instead.
        methods_without_wrappers = {}
        for name, func in self.tool_funcs.items():
            method_with_descriptor = create_tool_method(func, class_obj)
            methods_without_wrappers[name] = method_with_descriptor
        ########## Part 2: Create the service which offers those methods ################
        # In gRPC jargon, the service is the collection of methods and descriptors which
        # gets registered to the actual server software. Y'know the thing listening for
        # traffic on the socket?
        self._service = toproto.methods_to_service(
            funcs=[
                (method.func, method.input_type, method.output_type)
                for method in methods_without_wrappers.values()
            ],
            package=class_obj.__class__.__name__,
            descriptor_pool=descriptor_pool.Default(),
        )

        ########## Part 3: build the request handlers which wrap each method ################
        # We must also fullfill Google's fetish for context objects in order to actually
        # service the requests, so since we left the protobuf compiler on the curb, here we
        # go!!!

        def _request_handler(
            method, class_instance, request, context: grpc.ServicerContext
        ):
            """
            This is what actually gets called by the GRPC server to execute
            your app's method.
            """

            for metadatum in context.invocation_metadata():
                if metadatum.key == "get_desc":
                    # add metadata to response and send back empty PB
                    metadata = (
                        (
                            "truffle_tool_desc",
                            method.func.__truffle_description__,
                        ),
                    )
                    if (
                        hasattr(method.func, "__truffle_type__")
                        and method.func.__truffle_type__
                    ):
                        metadata += (
                            ("truffle_return_type", method.func.__truffle_type__),
                        )
                        print("desc", method.func.__truffle_description__)
                        print("type", method.func.__truffle_type__)
                    if method.func.__truffle_icon__:
                        metadata += (
                            ("truffle_tool_icon", method.func.__truffle_icon__),
                        )
                    if method.func.__truffle_args__:
                        for (
                            var_name,
                            var_desc,
                        ) in method.func.__truffle_args__.items():
                            metadata += ((var_name, var_desc),)
                    context.set_trailing_metadata(metadata)
                    return method.output_class()

            # Convert protobuf message to disctionary, actually *call* the function here.
            # this should be self rolled it causes a lot of issues and is fairly trivial
            args_dict = None
            try:
                args_dict = MessageToDict(
                    request,
                    always_print_fields_with_no_presence=True,
                    preserving_proto_field_name=True,
                    descriptor_pool=descriptor_pool.Default(),
                )
            except Exception as e:
                print("Using deprecated MessageToDict")
                args_dict = MessageToDict(
                    request,
                    preserving_proto_field_name=True,
                    descriptor_pool=descriptor_pool.Default(),
                )

            for field in method.input_class.DESCRIPTOR.fields:
                if field.name in args_dict:
                    if is_numeric_field(field):
                        if is_float_field(field):
                            args_dict[field.name] = float(args_dict[field.name])
                        else:
                            args_dict[field.name] = int(args_dict[field.name])
            args = list(args_dict.values())

            # now we populate an instance of the output protobuf object with the results
            # of calling the original method from the app
            ret_pb = method.output_class()
            try:
                ret_val = method.func(class_instance, *args)
                for field in ret_pb.DESCRIPTOR.fields:
                    if field.name == "return_value":
                        field_type = field.type
                        is_map = (
                            field.message_type
                            and field.message_type.has_options
                            and field.message_type.GetOptions().map_entry
                        )

                        if is_map:
                            # Handle map fields
                            if isinstance(ret_val, dict):
                                map_field = getattr(ret_pb, field.name)
                                log.info(
                                    f"setting map field {field.name}->{map_field} to {ret_val}"
                                )
                                # might need to recursively stringify the keys or someshit
                                map_field.update(ret_val)
                        elif (
                            field.label == FieldDescriptor.LABEL_REPEATED
                        ):  # and field_type is not FieldDescriptor.TYPE_MESSAGE:
                            # Handle repeated fields
                            if isinstance(ret_val, (list, tuple)):
                                getattr(ret_pb, field.name).extend(ret_val)
                            else:
                                getattr(ret_pb, field.name).append(ret_val)
                        else:
                            # Handle single value fields
                            if field_type == FieldDescriptor.TYPE_MESSAGE:
                                # For nested message types
                                log.info("nested message type: ", field.message_type)

                                if isinstance(ret_val, dict):
                                    getattr(ret_pb, field.name).ParseFromDict(ret_val)
                                else:
                                    nested = getattr(ret_pb, field.name)

                                    log.info("nested: ", type(nested))
                                    nested = ret_val
                            else:
                                # For primitive types
                                log.info(f"setting {field.name} to {ret_val}")
                                setattr(ret_pb, field.name, ret_val)
            except Exception as e:
                error_str = f"Tool Call Error!\n Error: f{e}\n Traceback: {traceback.format_exc()}"
                log.info("error: ", e)
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Error running tool: \n" + error_str)
                return ret_pb
            context.set_code(grpc.StatusCode.OK)
            context.set_details("Tool ran successfully")
            return ret_pb

        ########## Part 4: Build the fully baked gRPC service method objects
        self.grpc_service_methods = {}
        for (
            method_name,
            method_without_wrapper,
        ) in methods_without_wrappers.items():
            fully_baked_grpc_method = method_without_wrapper
            fully_baked_grpc_method.wrapper = functools.partial(
                _request_handler,
                method_without_wrapper,
                class_obj,
            )
            self.grpc_service_methods[method_name] = fully_baked_grpc_method

    def launch(self, socket_path: str = APP_SOCK):
        """
        Spin up a gRPC server, register our generated service and launch the server.
        """

        class AppService(self._service.service_class):
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
