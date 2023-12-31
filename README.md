# FletBox <img src=https://openclipart.org/download/183014 height=45 align=top>
A box for flet, abusing contextmanagers and decorators.

FletBox is a gradio/nicegui style wrapper around [flet](https://flet.dev/), handling the routing & syntax for you.

## Usage

**NOTE: for those who used fletbox<0.3, the syntax has changed and therefore your code will break.**

**I promise though, the new syntax is definitely cleaner!**

### Installation
```
pip install fletbox
```

### Import
```python
import flet as ft
from fletbox import FletBox, Builder, Factory
```

### Initialization
*NOTE: you can pass normal ft.app kwargs to FletBox.*
```python
fb = FletBox(view=ft.AppView.WEB_BROWSER)
```
kwargs can also be set via AttrDict.
```python
fb.kwargs.port = 8550
```

### Main Block, decorators and routing
The view routing is handled in the background.

This decorator is used for routing, and all decorated views take two inputs, page and builder.
```python
@fb.view("/")
def test(page: ft.Page):
```

EXTRA: the standard page.go function can be used for traveling between routes.
```python
page.go("/")
```

### Main Block, contextmanagers (with statements)
The syntax is drastically altered from the standard flet library.

```python
@fb.view("/")
def test(page: ft.Page) -> None:
    with page.Container(expand=True, margin=-10, gradient=page.standard_gradient): #can used stored attributes using "page" as a shared storage
        with page.Row() as row: #can be assigned, or not
            row.controls.append(ft.ElevatedButton("FletBox")) #see above
            page.ElevatedButton("FletBox")
            textfield = page.TextField(label="FletBox", text_size=20) #can be assigned, or not - for modification/reads

    @page.postexec #OPTIONAL: postexec decorator - run function after view load
    def postfunc():
        pass #YOUR_POST_FUNCTION_HERE

#can define whatever non-view-specific thing you want, passing target is optional
def shared_methods(page: ft.Page):
    page.fonts = {
        "Raleway": "assets/Raleway[wght].ttf"
    }
    page.theme = ft.Theme(color_scheme_seed="pink", visual_density="COMFORTABLE", font_family="Raleway")
    page.standard_gradient = ft.LinearGradient(begin=ft.alignment.bottom_left, end=ft.alignment.top_right, colors=["#F7C35A", "#FBAFAB"])
```

And finally we run the application.

*NOTE: you can pass normal ft.app kwargs to fb.app.*
```python
#pass normal ft.app kwargs to fb.app
fb.app(target=shared_methods)
```

## Other Usage
### Custom Elements
```python
import flet as ft
from fletbox import FletBox, Builder, Factory

#module with custom components
import flet_material as fm
fm.Theme.set_theme("earth") #whatever theme you want

#factory generates builders
factory = Factory(modules={"fm": fm})

#pass custom factory
fb = FletBox(factory=factory)

#fletbox decorator for routing
@fb.view("/")
def test(page: ft.Page) -> None:
    with page.Container(expand=True, margin=-10):
        #shell class in builder for fm due to custom factory
        page.fm.CheckBox(ft.BoxShape.CIRCLE, value=False, disabled=False)

fb.app()
```

### Verbosity
If you wish to disable printouts from fletbox, such as the follows:
```
SETUP completed in YOUR_TIME_HERE
127.0.0.1 connected to route / in YOUR_TIME_HERE
```
set verbose as False (must be run before fb.app):
```python
fb.verbose = False
```

### Wildcard URLs
If you want to make a dynamic view constructor:

The following code will match (e.g. /something/1) and pass wildcard=VALUE_IN_URL as kwargs
```python
@fb.view("/something/:wildcard")
def wildcard_example(page: ft.Page, wildcard:Any=...) -> None:
```

### Internal Builder
Unlike in fletbox<=0.2.13, the layout subclass for controls no longer exists as the contextmanagers and items controls were merged.

However, there is still an underlying builder subclass that was merged into page - for advanced uses it can be accessed in a few different ways.

It is important to note that the builder is *stateless*, as in it is refreshed on every function / view invocation.

Access via legacy args method as following
```python
@fb.view("/")
def test(page: ft.Page, builder: Builder) -> Builder:
    with builder.Container(expand=True, margin=-10, gradient=page.standard_gradient):
        with builder.Row() as row:
            row.controls.append(ft.ElevatedButton("FletBox"))
            builder.ElevatedButton("FletBox")
            textfield = builder.TextField(label="FletBox", text_size=20)
    return builder #you may return builder as optional, if you want to swap it
```

Access via internal value as following
```python
@fb.view("/")
def test(page: ft.Page) -> Builder:
    builder = page.builder
    with builder.Container(expand=True, margin=-10, gradient=page.standard_gradient):
        with builder.Row() as row:
            row.controls.append(ft.ElevatedButton("FletBox"))
            builder.ElevatedButton("FletBox")
            textfield = builder.TextField(label="FletBox", text_size=20)
    return builder #you may return builder as optional, if you want to swap it
```
