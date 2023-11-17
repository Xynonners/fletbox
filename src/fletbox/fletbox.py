# FletBox, written in 08/03/2023 to 08/05/2023
# typing decorators is extremely confusing so decorators are not type hinted in this project

import time

start_total = time.time()

from typing import (
    Callable,
)
from types import (
    ModuleType,
)

import inspect
import functools
from contextlib import contextmanager

import flet as ft
from rich import print
from simpleroute import BaseRouter

# dirty implementation of easydict
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
    def __setattr__(self, name, value):
        if not name in dir(dict):
            super(AttrDict, self).__setattr__(name, value)
        else:
            raise AttributeError(f"object attribute {repr(name)} is read-only")
    def __setitem__(self, name, value):
        if not name in dir(dict):
            super(AttrDict, self).__setitem__(name, value)
        else:
            raise AttributeError(f"object attribute {repr(name)} is read-only")

# filter elements with nonstandard controls inputs
def get_controls_from_module(m: ModuleType) -> list:
    elements = []
    for name, cls in vars(m).items():
        if inspect.isclass(cls):
            if issubclass(cls, ft.Control):
                elements.append(cls)
                common_matches = len([*set(dir(cls)).intersection(["controls", "actions", "content"])])
                uncommon_matches = len([*set(dir(cls)).intersection(["tabs", "title"])])
                if common_matches > 1 or uncommon_matches > 1:
                    print(f"[bold orange3]{name} matched \[{common_matches}c {uncommon_matches}u] possible subcontrol kwargs.[/bold orange3]")
    return elements

class Builder():

    modules = [ft]
    elements = [element for m in modules for element in get_controls_from_module(m)]

    get_controls_from_module = staticmethod(get_controls_from_module)

    #layout/items/extra distinction no longer neccessary due to smart pattern matching of controls/actions/content kwargs
    def __init__(self, extra_elements:list=[]) -> None:
        #not sure if we should be abusing edict here instead of using a shell class + setattr
        class _shell: pass

        #for building view tree
        self.root = ft.View()
        self.current = self.root

        #function to run after page load
        self.postfunc = None

        outer_self = self
        def wrap_control(cls: ft.Control):
            class wrapper(cls):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    #common occurances
                    if hasattr(outer_self.current, "controls"):
                        outer_self.current.controls.append(self)
                    elif hasattr(outer_self.current, "actions"):
                        outer_self.current.actions.append(self)
                    elif hasattr(outer_self.current, "content"):
                        outer_self.current.content = self
                    #uncommon occurances
                    elif hasattr(outer_self.current, "tabs"):
                        outer_self.current.tabs.append(self)
                    elif hasattr(outer_self.current, "title"):
                        outer_self.current.title = self
                def __enter__(self):
                    self.old_current = outer_self.current
                    outer_self.current = self
                def __exit__(self, *args):
                    outer_self.current = self.old_current
            return wrapper

        #create layout elements
        for element in self.elements:
            setattr(self, element.__name__, wrap_control(element))

        #create extra elements in alias shell class
        for alias, element in extra_elements:
            if not hasattr(self, alias):
                setattr(self, alias, _shell())
            setattr(getattr(self, alias), element.__name__, wrap_control(element))

    def postexec(self, func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        self.postfunc = wrapper
        return wrapper

class Factory():

    get_controls_from_module = staticmethod(get_controls_from_module)

    def set_controls_from_module(self, m: ModuleType, alias:str="") -> None:
        if not alias:
            alias = m.__name__
        elements = self.get_controls_from_module(m)
        self.extra_elements += [(alias, cls) for cls in elements]

    def __init__(self, modules:dict={}) -> None:
        self.extra_elements = []
        for alias, m in modules.items():
            self.set_controls_from_module(m, alias=alias)

    def Builder(self) -> Builder:
        return Builder(extra_elements=self.extra_elements)

class FletBox():
    @staticmethod
    def stub(page: ft.Page) -> None:
        pass

    def __init__(self, factory:Factory=Factory(), verbose:bool=True, catchall:str="/", target:Callable=stub, view:ft.AppView=ft.AppView.WEB_BROWSER, web_renderer:ft.WebRenderer=ft.WebRenderer.HTML, port:int=8550, **kwargs) -> None:
        #fletbox values
        self.factory = factory
        self.verbose = verbose
        self.catchall = catchall
        #flet values
        self.target = target
        self.kwargs = AttrDict(kwargs)
        self.kwargs.update({"view": view, "web_renderer": web_renderer, "port": port})
        #internal values
        self.funcs = {}

    def app(self, target:Callable=stub, **kwargs) -> None:
        #target again
        self.target = target
        #merge app kwargs with init kwargs
        self.kwargs.update(kwargs)
        #repopulate funcs via wrappers
        for wrapper in self.funcs.values(): wrapper()
        self.router = BaseRouter([*self.funcs.keys()], catchall=self.catchall)
        if self.verbose: print(""); print(self.router)

        def wrapped_target(page: ft.Page):
            #routing functions
            def route_change(e: ft.RouteChangeEvent):
                start = time.time()
                page.views.clear()
                path, kwargs = self.router.match(e.route)
                builder = self.funcs[path](e.route, page, **kwargs)
                page.views.append(builder.root)
                page.go(e.route)
                if builder.postfunc: builder.postfunc()
                end = time.time()
                if self.verbose: print(f"{page.client_ip} connected to [bold blue]{e.route}[/bold blue] ╍ [bold red]{path}[/bold red] in {round(end - start, 8)}")
            def view_pop(view):
                page.views.pop()
                top_view = page.views[-1]
                page.go(top_view.route)

            #run provided target
            self.target(page)

            #routing
            page.on_route_change = route_change
            page.on_view_pop = view_pop
            page.go(page.route)

        self.kwargs["target"] = wrapped_target

        end_total = time.time()
        if self.verbose: print(f"[bold green]SETUP[/bold green] completed in {round(end_total - start_total, 8)}")
        ft.app(**self.kwargs)

    #wrap method to provide builder, return ft.View
    def _view(self, factory: Factory):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(route: str, page: ft.Page, **kwargs):
                builder = factory.Builder()
                #allow our page class to access methods from builder
                #https://stackoverflow.com/questions/38541015/how-to-monkey-patch-a-call-method
                page.builder = builder
                class BuilderPage(type(page)):
                    def __getattr__(self, attr):
                        return getattr(self.builder, attr)
                page.__class__ = BuilderPage
                #custom DI - dirty but may be useful for more explicit code
                optional_args = {"builder": builder}
                pass_args = {}
                for k in inspect.getfullargspec(func).args:
                    if k in optional_args.keys():
                        pass_args.update({k: optional_args[k]})
                ret = func(page, **pass_args, **kwargs); builder = ret if isinstance(ret, Builder) else builder
                builder.root.route = route
                return builder
            return wrapper
        return decorator

    #replace method with function creator, initial update with wrapper
    def view(self, path: str):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper():
                self.funcs.update({path: self._view(self.factory)(func)})
            self.funcs.update({path: wrapper})
            return wrapper
        return decorator

