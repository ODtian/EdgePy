import json
import os

import clr

from webview2.error import GuiNotInitializedError
from webview2.lib import path as lib_path
from webview2.utils import Event, invoke_in_gui, is_64bit, js_api, try_except

os.environ["Path"] += f";{lib_path / 'x64' if is_64bit() else 'x86'}"
clr.AddReference(str(lib_path / "Microsoft.Web.WebView2.Core.dll"))
clr.AddReference(str(lib_path / "Microsoft.Web.WebView2.Wpf.dll"))
clr.AddReference(str(lib_path / "ControlzEx.dll"))
clr.AddReference(str(lib_path / "Microsoft.Xaml.Behaviors.dll"))

from Microsoft.Web.WebView2.Wpf import WebView2
from System import Action, Func, Type, Uri
from System.Drawing import Color, Size
from System.IO import StreamReader
from System.Threading import ApartmentState, Thread, ThreadStart
from System.Threading.Tasks import Task
from System.Windows import (
    Application,
    CornerRadius,
    Interop,
    ResizeMode,
    Thickness,
    WindowStartupLocation,
    WindowState,
    WindowStyle,
)
from System.Windows.Controls import Border
from System.Windows.Markup import XamlReader
from System.Windows.Media import BrushConverter
from System.Windows.Shell import NonClientFrameEdges, WindowChrome


class NotInitializedGui:
    def __getattr__(self, name):
        raise GuiNotInitializedError()

    def __setattr__(self, name, value):
        raise GuiNotInitializedError()


class WpfGui:
    instances = []
    app = None
    app_created = None

    class CookieManager:
        def __init__(self, gui):
            self.gui = gui

        def invoke(self, func):
            return self.gui.invoke(func)

        @invoke_in_gui
        def add_cookie(self, name, value, domain=None, path=None):
            cookie = self.gui.browser.web_view.CoreWebView2.CookieManager.CreateCookie(
                name, value, domain, path
            )
            self.gui.browser.web_view.CoreWebView2.CookieManager.AddOrUpdateCookie(
                cookie
            )

    class IPCHandler:
        def __init__(self, gui):
            self.gui = gui
            self.handle_ipc = None

        def invoke(self, func):
            return self.gui.invoke(func)

        def initialize(self):
            self.evaluate_js(
                js_api,
                lambda *_: self.gui.window.navigated.set(
                    str(self.gui.browser.web_view.Source)
                ),
            )

        def handle_web_message(self, message_type, data):
            self.handle_ipc(message_type, data)

        @invoke_in_gui
        def evaluate_js(self, script, callback=None):
            try:
                self.gui.browser.web_view.ExecuteScriptAsync(script).ContinueWith(
                    Action[Task](
                        lambda task: callback(json.loads(task.Result), False)
                        if callback
                        else None
                    )
                )
            except Exception as e:
                if callback:
                    callback(e, True)

    class NavigateHandler:
        def __init__(self, gui):
            self.gui = gui

        def invoke(self, func):
            return self.gui.invoke(func)

        @invoke_in_gui
        def navigate_to(self, url):
            self.gui.browser.web_view.Source = Uri(url)

    def __init__(
        self,
        title,
        size=None,
        position=None,
        resizable=True,
        frameless=False,
        transparent=False,
        background=None,
        topmost=False,
        hidden=False,
        maximized=False,
        minimized=False,
        xaml=None,
        xaml_path=str(lib_path / "Main.xaml"),
    ):
        # self.window = window
        self.window = None

        if not frameless and transparent:
            print("Transparent window must be frameless")

        self._title = title
        self._xaml = xaml
        self._xaml_path = xaml_path
        self._size = size
        self._position = position
        self._resizable = resizable
        self._frameless = frameless
        self._transparent = transparent
        self._background = background
        self._topmost = topmost
        self._hidden = hidden
        self._maximized = maximized
        self._minimized = minimized
        # self.gui_window = XamlReader.Load(
        #     StreamReader(str(lib_path / "Main.xaml")).BaseStream
        # )

        # self.title = self.window.title

        # if self.window.size:
        #     self.size = self.window.size

        # if self.window.position:
        #     self.position = self.window.position
        # else:
        #     self.gui_window.WindowStartupLocation = WindowStartupLocation.CenterScreen

        # self.resizable = self.window.resizable

        # if not self.window.frameless and self.window.transparent:
        #     print("Transparent window must be frameless")

        # self.frameless = self.window.frameless or self.window.transparent
        # self.transparent = self.window.transparent

        # if self.window.background:
        #     self.background = self.window.background

        # self.topmost = self.window.topmost

        # if self.window.hidden:
        #     self.hide()
        # elif self.window.maximized:
        #     self.maximize()
        # elif self.window.minimized:
        #     self.maximize()
        # else:
        #     self.show()

        # self.handle = int(Interop.WindowInteropHelper(self.gui_window).Handle.ToInt64())

        # self.browser = Edge(self.gui_window, window)
        # self.url = self.window.url

        # self.gui_window.IsVisibleChanged += self._on_shown
        # self.gui_window.Closed += self._on_closed
        # self.gui_window.Closing += self._on_closing

        # self.instances.append(self.window)

    def _on_shown(self, sender, args):
        if sender.IsVisible:
            self.window.shown.set()

    def _on_closed(self, sender, args):
        self.instances.remove(self.window)
        self.window.closed.set()

    def _on_closing(self, sender, args):
        self.window.closing.set()

    @classmethod
    def create(
        cls,
        title,
        size=None,
        position=None,
        resizable=True,
        frameless=False,
        transparent=False,
        background=None,
        topmost=False,
        hidden=False,
        maximized=False,
        minimized=False,
        xaml=None,
        xaml_path=str(lib_path / "Main.xaml"),
    ):
        gui = cls(
            title=title,
            size=size,
            position=position,
            resizable=resizable,
            frameless=frameless,
            transparent=transparent,
            background=background,
            topmost=topmost,
            hidden=hidden,
            maximized=maximized,
            minimized=minimized,
            xaml=xaml,
            xaml_path=xaml_path,
        )
        return (
            gui,
            cls.CookieManager(gui),
            cls.IPCHandler(gui),
            cls.NavigateHandler(gui),
        )

    def initialize(self, window):
        self.window = window

        self.gui_window = (
            XamlReader.Load(StreamReader(str(lib_path / self._xaml_path)).BaseStream)
            if self._xaml_path
            else XamlReader.Parse(self._xaml)
        )

        self.title = self._title

        if self._size:
            self.size = self._size

        if self._position:
            self.position = self._position
        else:
            self.gui_window.WindowStartupLocation = WindowStartupLocation.CenterScreen

        self.resizable = self._resizable
        self.frameless = self._frameless or self._transparent
        self.transparent = self._transparent

        if self._background:
            self.background = self._background

        self.topmost = self._topmost

        if self._hidden:
            self.hide()
        elif self._maximized:
            self.maximize()
        elif self._minimized:
            self.maximize()
        else:
            self.show()

        self.handle = int(Interop.WindowInteropHelper(self.gui_window).Handle.ToInt64())

        self.browser = Edge(self.gui_window, self.window)

        self.gui_window.IsVisibleChanged += self._on_shown
        self.gui_window.Closed += self._on_closed
        self.gui_window.Closing += self._on_closing

        self.instances.append(self.window)

    def begin_invoke(self, func):
        return self.gui_window.Dispatcher.BeginInvoke(Func[Type](func))

    def invoke(self, func):
        return self.gui_window.Dispatcher.Invoke(Func[Type](func))

    # title
    @property
    def title(self):
        return self.gui_window.Title

    @title.setter
    @invoke_in_gui
    def title(self, title):
        self.gui_window.Title = title

    # size
    @invoke_in_gui
    def resize(self, width, height):
        self.gui_window.Width = width
        self.gui_window.Height = height

    @property
    def size(self):
        return self.gui_window.Width, self.gui_window.Height

    @size.setter
    def size(self, size):
        self.resize(*size)

    # position
    @invoke_in_gui
    def move(self, dx, dy):
        self.gui_window.Left += dx
        self.gui_window.Top += dy

    @invoke_in_gui
    def move_abs(self, x, y):
        self.gui_window.Left = x
        self.gui_window.Top = y

    @property
    def position(self):
        return self.gui_window.Left, self.gui_window.Top

    @position.setter
    def position(self, position):
        self.move_abs(*position)

    # resizable
    @property
    def resizable(self):
        return not self.gui_window.ResizeMode == ResizeMode.NoResize

    @resizable.setter
    @invoke_in_gui
    def resizable(self, resizable):
        self.gui_window.ResizeMode = (
            ResizeMode.CanResize if resizable else ResizeMode.NoResize
        )

    # frameless
    @property
    def frameless(self):
        return self.gui_window.WindowStyle == getattr(WindowStyle, "None")

    @frameless.setter
    @invoke_in_gui
    def frameless(self, frameless):
        if frameless:
            self.gui_window.WindowStyle = getattr(WindowStyle, "None")
            chrome = WindowChrome()
            # WindowChrome 屁用没有
            # chrome.NonClientFrameEdges = (
            #     NonClientFrameEdges.Left
            #     | NonClientFrameEdges.Right
            #     | NonClientFrameEdges.Bottom
            # )
            # chrome.ResizeBorderThickness = Thickness(5.0)
            # chrome.GlassFrameThickness = Thickness(-1.0)
            WindowChrome.SetWindowChrome(self.gui_window, chrome)
            self.gui_window.FindName("Grid").Margin = Thickness(1.0)
        else:
            self.gui_window.WindowStyle = WindowStyle.SingleBorderWindow
            WindowChrome.SetWindowChrome(self.gui_window, None)
            self.gui_window.FindName("Grid").Margin = Thickness(0.0)

    # transparent
    @property
    def transparent(self):
        return self.gui_window.AllowsTransparency

    @transparent.setter
    @invoke_in_gui
    def transparent(self, transparent):
        if not self.window.shown.is_set():
            self.gui_window.AllowsTransparency = transparent

    # background
    @property
    def background(self):
        return self.gui_window.Background

    @background.setter
    @invoke_in_gui
    def background(self, background):
        self.gui_window.Background = BrushConverter().ConvertFrom(background)

    # topmost
    @property
    def topmost(self):
        return self.gui_window.Topmost

    @topmost.setter
    @invoke_in_gui
    def topmost(self, topmost):
        self.gui_window.Topmost = topmost

    @invoke_in_gui
    def show(self):
        self.gui_window.Show()

    @invoke_in_gui
    def normalize(self):
        self.gui_window.WindowState = WindowState.Normal

    @invoke_in_gui
    def maximize(self):
        self.gui_window.WindowState = WindowState.Maximized

    @invoke_in_gui
    def minimize(self):
        self.gui_window.WindowState = WindowState.Minimized

    @invoke_in_gui
    def hide(self):
        self.gui_window.Hide()

    @invoke_in_gui
    def close(self):
        self.gui_window.Close()

    # @invoke_in_gui
    # def evaluate_js(self, script, callback=None):
    #     self.browser.evaluate_js(script, callback)


class Edge:
    @try_except
    def __init__(self, gui_window, window):
        self.gui_window = gui_window
        self.window = window

        self.web_view = WebView2()
        self.web_view.DefaultBackgroundColor = Color.Transparent

        self.web_view.CoreWebView2InitializationCompleted += self._on_ready
        self.web_view.NavigationCompleted += self._on_navigation_completed
        self.web_view.WebMessageReceived += self._on_web_message
        self.web_view.Source = Uri(self.window.url)

        self.gui_window.FindName("Grid").Children.Add(self.web_view)

    def _on_web_message(self, sender, args):
        self.window.ipc.handle_web_message(*json.loads(args.WebMessageAsJson))

    def _on_ready(self, sender, args):
        self.web_view.CoreWebView2.NewWindowRequested += self._on_new_window_requested
        self.window.ready.set()

    def _on_new_window_requested(self, sender, args):
        args.Handled = True
        self.window.new_window.set(args.Name, str(args.Uri))

    def _on_navigation_completed(self, sender, args):
        self.window.ipc.initialize()

    # def evaluate_js(self, script, callback=None):
    #     try:
    #         self.web_view.ExecuteScriptAsync(script).ContinueWith(
    #             Action[Task](
    #                 lambda task: callback(json.loads(task.Result), False)
    #                 if callback
    #                 else None
    #             )
    #         )
    #     except Exception as e:
    #         if callback:
    #             callback(e, True)


async def initialize_gui(*windows):
    windows = list(windows)

    if not WpfGui.instances:
        if not WpfGui.app_created:
            WpfGui.app_created = Event()

        @try_except
        def create():
            master = windows.pop(0)
            master.gui.initialize(master)

            WpfGui.app = Application()
            WpfGui.app.Startup += lambda *_: WpfGui.app_created.set()
            WpfGui.app.Run(master.gui.gui_window)

        thread = Thread(ThreadStart(create))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()

    await WpfGui.app_created.wait()

    master = WpfGui.instances[0]
    for window in windows:
        master.gui.begin_invoke(lambda: window.gui.initialize(window))
