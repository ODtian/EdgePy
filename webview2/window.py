import asyncio
import json
from uuid import uuid4

from webview2.error import JSError
from webview2.utils import Event, try_call


class Window:
    def __init__(
        self,
        url,
        js_api=(),
        gui=None,
        cookie_manager=None,
        ipc=None,
        navigate_handler=None,
    ):
        self._future_map = {}
        self._js_api = {}
        self._loop = asyncio.get_running_loop()

        self.shown = Event()
        self.ready = Event()
        self.navigated = Event(init_args=url)
        self.new_window = Event()
        self.closing = Event()
        self.closed = Event()

        self.js_api = js_api
        self.gui = gui
        self.cookie_manager = cookie_manager
        self.ipc = ipc
        self.navigate_handler = navigate_handler

        self.ipc.handle_ipc = self._handle_ipc

    def _call_python(self, call_id, name, args):
        async def _call():
            await self.call(
                "webview._resultOk",
                call_id,
                *(await try_call(self._js_api[name], args)),
            )

        asyncio.create_task(_call())

    def _result_ok(self, call_id, result, is_exc):
        future = self._future_map.pop(call_id)

        if result is not None:
            result = json.loads(result)

        if not future.done():
            if is_exc:
                future.set_exception(JSError(result))
            else:
                future.set_result(result)

    def _handle_ipc(self, message_type, data):
        if message_type == 0:
            self._loop.call_soon_threadsafe(self._call_python, *data)

        elif message_type == 1:
            self._loop.call_soon_threadsafe(self._result_ok, *data)

    @property
    def url(self):
        return self.navigated.args

    @url.setter
    def url(self, url):
        self.navigate_handler.navigate_to(url)

    @property
    def js_api(self):
        return tuple(self._js_api.values())

    @js_api.setter
    def js_api(self, apis):
        self._js_api = {api.__name__: api for api in apis}

    async def call(self, name, *args):
        return await self.evaluate_js(
            f"return {name}(...JSON.parse({repr(json.dumps(args))}))"
        )

    async def evaluate_js(self, script):
        call_id = uuid4().hex
        future = self._future_map[call_id] = self._loop.create_future()

        def callback(result, is_exc):
            if is_exc and not future.done():
                self._loop.call_soon_threadsafe(future.set_exception, result)

        self.ipc.evaluate_js(
            f"webview._callJs('{call_id}', async () => {{ {script} }})", callback
        )

        return await future

    async def fetch_url(self, url):
        self.navigated.clear()
        self.url = url
        await self.navigated.wait()

    async def fetch_js(self, url):
        await self.call("webview._fetchJs", url)

    def add_cookie(self, name, value, domain=None, path=None):
        self.cookie_manager.add_cookie(name, value, domain, path)
