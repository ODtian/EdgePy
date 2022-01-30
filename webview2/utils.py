import asyncio
import platform
import traceback
from functools import wraps
from pynput import mouse

from webview2.js import path as js_path

with (js_path / "api.js").open() as f:
    js_api = f.read()


def try_except(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            print(func.__name__, e)
            raise e

    return inner


class DragMover:
    def __init__(self, window):
        self.window = window
        self.last_x = self.now_x = 0
        self.last_y = self.now_y = 0
        self.listener = None
        self.controller = mouse.Controller()

    @property
    def dx(self):
        return self.now_x - self.last_x

    @property
    def dy(self):
        return self.now_y - self.last_y

    def on_move(self, x, y):
        self.last_x = self.now_x
        self.last_y = self.now_y
        self.now_x, self.now_y = self.controller.position
        self.window.gui.move(self.dx, self.dy)

    def on_click(self, x, y, button, pressed):
        if self.listener and not pressed:
            self.stop_drag()

    async def start_drag(self, x, y):
        self.last_x = self.now_x = x
        self.last_y = self.now_y = y
        self.listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        self.listener.start()

    def stop_drag(self):
        self.listener.stop()
        self.listener = None


class Event(asyncio.Event):
    def __init__(self, init_args=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.args = init_args

    def set(self, *args):
        self._loop.call_soon_threadsafe(super().set)
        self.args = args or None

    async def wait(self):
        await super().wait()
        return self.args


# class ListeningEvent(asyncio.Event):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.callbacks = []

#     async def _callback(self, callback, *args, **kwargs):
#         if await callback(*args, **kwargs):
#             self.callbacks.remove(callback)

#     def _set(self, *args, **kwargs):
#         super().set()

#         asyncio.gather(
#             *(self._callback(callback, *args, **kwargs) for callback in self.callbacks),
#             loop=self._loop,
#         )

#     def set(self, *args, **kwargs):
#         self._loop.call_soon_threadsafe(
#             lambda: self._set(*args, **kwargs),
#         )

#     async def wait(self):
#         await super().wait()

#     def __add__(self, callback):
#         self.callbacks.append(callback)
#         return self

#     def __sub__(self, callback):
#         self.callbacks.remove(callback)
#         return self


def invoke_in_gui(func):
    @wraps(func)
    def wrap(self, *args, **kwargs):
        return self.invoke(lambda: func(self, *args, **kwargs))

    return wrap


async def try_call(method, args):
    try:
        return await method(*args), False

    except Exception as e:
        return {
            "message": str(e),
            "name": type(e).__name__,
            "stack": traceback.format_exc(),
        }, True


def is_64bit():
    return platform.architecture()[0] == "64bit"


def a(func):
    @wraps(func)
    async def inner(*args, **kwargs):
        return func(*args, **kwargs)

    return inner
