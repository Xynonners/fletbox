# FletBox <img src=https://openclipart.org/download/183014 height=45 align=top>
A box for flet, abusing contextmanagers and decorators.

FletBox is a wrapper around [flet](https://flet.dev/), handling the routing & syntax for you.

## Usage

### Installation
```
pip install fletbox
```

### General Example
```python
import flet as ft
from fletbox import FletBox, Builder, Factory

#pass normal ft.app kwargs to FletBox, can also be set (eg. fb.port=8000)
fb = FletBox()

#fletbox decorator for routing, use page.go(YOUR_ROUTE_HERE) for traveling between views
@fb.view("/")
def test(page: ft.Page, builder: Builder) -> Builder:
    #builder.layout is contextmanagers, remap via layout=builder.layout
    with builder.layout.Container(expand=True, margin=-10, gradient=page.standard_gradient):
        #can also do with YOUR_X as YOUR_Y: since control is yielded in contextmanager
        with builder.layout.Row() as row:
            row.controls.append(ft.ElevatedButton("FletBox"))
            #builder attrs for creating deepest control
            builder.ElevatedButton("FletBox")
            #assign if modification/reads are required
            textfield = builder.TextField(label="FletBox", text_size=20)
    #returning builder is optional
    return builder

#can define whatever non-view-specific thing you want, passing target is optional
def shared_methods(page: ft.Page):
    page.fonts = {
        "Raleway": "assets/Raleway[wght].ttf"
    }
    page.theme = ft.Theme(color_scheme_seed="pink", visual_density="COMFORTABLE", font_family="Raleway", use_material3=False)
    page.standard_gradient = ft.LinearGradient(begin=ft.alignment.bottom_left, end=ft.alignment.top_right, colors=["#F7C35A", "#FBAFAB"])

#pass normal ft.app kwargs to fb.app, can also be set (eg. fb.port=8000)
fb.app(target=shared_methods)
```
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
def test(page: ft.Page, builder: Builder) -> None:
    with builder.layout.Container(expand=True, margin=-10):
        #shell class in builder for fm due to custom factory, builder.fm.layout also exists
        builder.fm.Checkbox(ft.BoxShape.CIRCLE, value=False, disabled=False)

fb.app()
```
