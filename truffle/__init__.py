import inspect
import os
import logging
import typing


from .truffle_app import TruffleApp, AppMetadata  # noqa: F401
from .client import TruffleClient, TruffleReturnType, TruffleFile  # noqa: F401

__all__ = ["TruffleApp", "TruffleClient", "AppMetadata", "TruffleFile"]

__version__ = "0.6.2"
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


def internal_fn1(*args):
    pass


def extract_all_top_level_functions(module):
    """
    Extracts all top-level functions from a given module.
    Returns a dictionary of function names to function objects.
    """
    functions = {}
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # Ensure the function is defined in the module (not imported)
        if obj.__module__ == module.__name__:
            functions[name] = obj
            # Check if the function is decorated
            # if hasattr(obj, '__wrapped__'):
            #     functions[name] = obj
            # else:
    return functions


def args(**kwargs):
    """
    Add extra info for the Agent to understand tool arguments

    Your function args should be passed as named args to the decorator, so
    if your tool's core function is `def foo(self, bar)` then you would decorate
    it with `@truffle.args(bar="description of bar")`
    """

    def decorator(func):
        func.__truffle_args__ = kwargs
        return func

    return decorator


def tool(description: str = None, icon: str = None):
    """
    Expose this method as a tool to the Agent.

    Description is used to give the Agent more info about the tool, and the icon is an SF Symbol name in the UI
    """

    def decorator(func):
        func.__truffle_tool__ = True
        func.__truffle_icon__ = icon
        func.__truffle_description__ = description
        # if return type is TruffleFile or TruffleImage - base of TruffleReturnType
        ret_type = typing.get_type_hints(func).get("return", None)
        if (
            ret_type
            and hasattr(ret_type, "__bases__")
            and issubclass(ret_type, TruffleReturnType)
        ):
            func.__truffle_type__ = ret_type.__name__
        if not hasattr(func, "__truffle_args__"):
            func.__truffle_args__ = None
        return func

    return decorator
