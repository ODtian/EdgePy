import asyncio

from webview2.gui import WpfGui, initialize_gui
from webview2.utils import DragMover, a
from webview2.window import Window


def create_window(
    title,
    url,
    size=None,
    position=None,
    resizable=True,
    frameless=False,
    transparent=False,
    background=None,
    topmost=False,
    maximized=False,
    minimized=False,
    hidden=False,
    js_api=(),
):
    gui, cookie_manager, ipc, navigate_handler = WpfGui.create(
        title=title,
        size=size,
        position=position,
        resizable=resizable,
        frameless=frameless,
        transparent=transparent,
        background=background,
        topmost=topmost,
        maximized=maximized,
        minimized=minimized,
        hidden=hidden,
    )
    return Window(
        url,
        js_api=js_api,
        gui=gui,
        cookie_manager=cookie_manager,
        ipc=ipc,
        navigate_handler=navigate_handler,
    )


async def start_windows(*windows, join=True):
    await initialize_gui(*windows)
    if join:
        await asyncio.gather(*(window.closed.wait() for window in windows))


__all__ = ["DragMover", "Window", "create_window", "start_windows", "a"]
