from . import properties
from . import library
from . import generator
from . import swap
from . import export
from . import authoring
from . import tools
from . import ui

modules = (properties, library, generator, swap, export, authoring, tools, ui)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
