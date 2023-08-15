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

class Builder():

    all_elements, filtered_elements = [], []

    # filter elements with nonstandard controls inputs
    @staticmethod
    def get_controls_from_module(m: ModuleType) -> (list, list):
        all_elements, filtered_elements = [], []
        for name, cls in vars(m).items():
            if inspect.isclass(cls):
                if issubclass(cls, ft.Control):
                    all_elements.append(cls)
                    if len([*set(dir(cls)).intersection(["controls", "actions", "content"])]) >= 1:
                        filtered_elements.append(cls)
        return all_elements, filtered_elements

    modules = [ft]
    for m in modules:
        tup = get_controls_from_module(m)
        all_elements += tup[0]
        filtered_elements += tup[1]

    #layout/items/extra distinction no longer neccessary due to smart pattern matching of controls/actions/content kwargs
    def __init__(self, extra_layout_elements:list=[], extra_items_elements:list=[]) -> None:
        #not sure if we should be abusing edict here instead of using a shell class + setattr
        class _shell: pass
        self.layout = _shell()

        #for building view tree
        self.root = ft.View()
        self.current = self.root

        #function to run after page load
        self.postfunc = None

        def layout(self, func: Callable):
            @functools.wraps(func)
            @contextmanager
            def context_manager(*args, **kwargs):
                old_current = self.current
                if hasattr(self.current, "controls"):
                    self.current.controls.append(func(*args, **kwargs))
                    self.current = self.current.controls[-1]
                elif hasattr(self.current, "actions"):
                    self.current.actions.append(func(*args, **kwargs))
                    self.current = self.current.actions[-1]
                elif hasattr(self.current, "content"):
                    self.current.content = func(*args, **kwargs)
                    self.current = self.current.content
                yield self.current
                self.current = old_current
            return context_manager

        def items(self, func:Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if hasattr(self.current, "controls"):
                    self.current.controls.append(func(*args, **kwargs))
                    return self.current.controls[-1]
                elif hasattr(self.current, "actions"):
                    self.current.actions.append(func(*args, **kwargs))
                    return self.current.actions[-1]
                elif hasattr(self.current, "content"):
                    self.current.content = func(*args, **kwargs)
                    return self.current.content
            return wrapper

        #create layout elements
        for element in self.filtered_elements:
            setattr(self.layout, element.__name__, layout(self, element))

        #create extra layout elements in alias shell class
        for alias, element in extra_layout_elements:
            if not hasattr(self, alias):
                setattr(self, alias, _shell())
                setattr(getattr(self, alias), "layout", _shell())
            setattr(getattr(self, alias).layout, element.__name__, layout(self, element))

        #create items elements
        for element in self.all_elements:
            setattr(self, element.__name__, items(self, element))

        #create extra items elements in alias shell class
        for alias, element in extra_items_elements:
            if not hasattr(self, alias):
                setattr(self, alias, _shell())
            setattr(getattr(self, alias), element.__name__, items(self, element))

    def postexec(self, func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        self.postfunc = wrapper
        return wrapper


class Factory():
    def set_controls_from_module(self, m: ModuleType, alias:str="") -> None:
        if not alias:
            alias = m.__name__
        tup = self.get_controls_from_module(m)
        self.extra_items_elements += [(alias, cls) for cls in tup[0]]
        self.extra_layout_elements += [(alias, cls) for cls in tup[1]]

    def __init__(self, modules:dict={}) -> None:
        self.extra_layout_elements = []
        self.extra_items_elements = []
        self.get_controls_from_module = Builder.get_controls_from_module
        for alias, m in modules.items():
            self.set_controls_from_module(m, alias=alias)

    def Builder(self) -> Builder:
        return Builder(extra_layout_elements=self.extra_layout_elements, extra_items_elements=self.extra_items_elements)

class FletBox():
    @staticmethod
    def stub(page: ft.Page) -> None:
        pass

    def __init__(self, factory:Factory=Factory(), verbose:bool=True, target:Callable=stub, view:ft.AppView=ft.AppView.WEB_BROWSER, web_renderer:ft.WebRenderer=ft.WebRenderer.HTML, port:int=8550, **kwargs) -> None:
        #fletbox values
        self.factory = factory
        self.verbose = verbose
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
        self.kwargs = {**kwargs, **self.kwargs}
        #repopulate funcs via wrappers
        for wrapper in self.funcs.values(): wrapper()
        self.router = BaseRouter([*self.funcs.keys()])
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
    @staticmethod
    def _view(factory: Factory):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(route: str, page: ft.Page, *args, **kwargs):
                builder = factory.Builder()
                ret = func(page, builder, *args, **kwargs); builder = ret if isinstance(ret, Builder) else builder
                builder.root.route = route
                return builder
            return wrapper
        return decorator

    #replace method with function creator, initial update with wrapper
    def view(self, path: str):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                self.funcs.update({path: self._view(self.factory)(func)})
            self.funcs.update({path: wrapper})
            return wrapper
        return decorator
