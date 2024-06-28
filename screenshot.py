from cefpython3 import cefpython as cef
import os
import platform
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image
except ImportError:
    print("Pillow is not installed. Install using: pip install pillow")
    sys.exit(1)


def main(url, w, h):
    global VIEWPORT_SIZE, URL, SCREENSHOT_PATH
    URL = url
    VIEWPORT_SIZE = (int(w), int(h))
    SCREENSHOT_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "SCREENSHOT.png")

    # Initialize CEF Python
    settings = {
        "windowless_rendering_enabled": True,
    }

    switches = {
        "disable-gpu": "",
        "disable-gpu-compositing": "",
        "enable-begin-frame-scheduling": "",
        "disable-surfaces": "",
    }

    cef.Initialize(settings=settings, switches=switches)

    try:
        sys.excepthook = cef.ExceptHook
    except AttributeError:
        pass

    check_versions()

    if os.path.exists(SCREENSHOT_PATH):
        print("Removing old screenshot")
        os.remove(SCREENSHOT_PATH)

    command_line_arguments()

    browser_settings = {
        "windowless_frame_rate": 30,
    }

    create_browser(browser_settings)

    cef.MessageLoop()
    cef.Shutdown()

    print("Opening your screenshot with the default application")
    open_with_default_application(SCREENSHOT_PATH)


def check_versions():
    ver = cef.GetVersion()
    print("CEF Python {ver}".format(ver=ver["version"]))
    print("Chromium {ver}".format(ver=ver["chrome_version"]))
    print("CEF {ver}".format(ver=ver["cef_version"]))
    print("Python {ver} {arch}".format(ver=platform.python_version(), arch=platform.architecture()[0]))
    assert cef.__version__ >= "66.0", "CEF Python v66.0+ required to run this program"


def command_line_arguments():
    if len(sys.argv) == 4:
        url = sys.argv[1]
        width = int(sys.argv[2])
        height = int(sys.argv[3])
        if url.startswith("http://") or url.startswith("https://"):
            global URL
            URL = url
        else:
            print("Error: Invalid URL Entered")
            sys.exit(1)
        if width > 0 and height > 0:
            global VIEWPORT_SIZE
            VIEWPORT_SIZE = (width, height)
        else:
            print("Error: Invalid Width and Height")
            sys.exit(1)
    elif len(sys.argv) > 1:
        print("Error: Expected Arguments Not Received. Expected Arguments are URL, Width, and Height")


def create_browser(settings):
    global VIEWPORT_SIZE, URL
    parent_window_handle = 0
    window_info = cef.WindowInfo()
    window_info.SetAsOffscreen(parent_window_handle)
    print("Viewport size: {size}".format(size=str(VIEWPORT_SIZE)))
    print("Loading URL: {url}".format(url=URL))
    browser = cef.CreateBrowserSync(window_info=window_info, settings=settings, url=URL)
    browser.SetClientHandler(LoadHandler())
    browser.SetClientHandler(RenderHandler())
    browser.SendFocusEvent(True)
    browser.WasResized()


def save_screenshot(browser):
    global SCREENSHOT_PATH
    buffer_string = browser.GetUserData("OnPaint.buffer_string")
    if not buffer_string:
        raise Exception("Buffer String was empty because OnPaint was never called")
    image = Image.frombytes("RGBA", VIEWPORT_SIZE, buffer_string, "raw", "RGBA", 0, 1)
    image.save(SCREENSHOT_PATH, "PNG")
    print("Saved screenshot to: {path}".format(path=SCREENSHOT_PATH))


def open_with_default_application(path):
    if sys.platform.startswith("darwin"):
        subprocess.call(["open", path])
    elif os.name == "nt":
        os.startfile(path)
    elif os.name == "posix":
        subprocess.call(["xdg-open", path])


def exit_app(browser):
    print("Closing browser and exiting application")
    browser.CloseBrowser()
    cef.QuitMessageLoop()


class LoadHandler(object):
    def OnLoadingStateChange(self, browser, is_loading, **_):
        if not is_loading:
            sys.stdout.write(os.linesep)
            print("Website has been loaded")
            save_screenshot(browser)
            cef.PostTask(cef.TID_UI, exit_app, browser)

    def OnLoadError(self, browser, frame, error_code, failed_url, **_):
        if not frame.IsMain():
            return
        print("Failed to load URL: {url}".format(url=failed_url))
        print("Error code: {code}".format(code=error_code))
        cef.PostTask(cef.TID_UI, exit_app, browser)


class RenderHandler(object):
    def __init__(self):
        self.OnPaint_called = False

    def GetViewRect(self, rect_out, **_):
        rect_out.extend([0, 0, VIEWPORT_SIZE[0], VIEWPORT_SIZE[1]])
        return True

    def OnPaint(self, browser, element_type, paint_buffer, **_):
        if self.OnPaint_called:
            sys.stdout.write(".")
            sys.stdout.flush()
        else:
            sys.stdout.write("OnPaint")
            self.OnPaint_called = True
        if element_type == cef.PET_VIEW:
            buffer_string = paint_buffer.GetBytes(mode='rgba', origin="top-left")
            browser.SetUserData("OnPaint.buffer_string", buffer_string)
        else:
            raise Exception("Unsupported element type in OnPaint")


# GUI Setup using tkinter
root = tk.Tk()
root.geometry("550x400")
root.title("Screenshot Capture")

frame = ttk.Frame(root, padding="20")
frame.pack(fill=tk.BOTH, expand=True)

obj1 = tk.StringVar()
obj2 = tk.StringVar()
obj3 = tk.StringVar()

def capture_screenshot():
    main(obj1.get(), obj2.get(), obj3.get())

# Widgets
label_url = ttk.Label(frame, text="Enter Website URL:")
label_url.pack(fill=tk.X, pady=5)
entry_url = ttk.Entry(frame, textvariable=obj1)
entry_url.pack(fill=tk.X, padx=20, pady=5)

label_width = ttk.Label(frame, text="Enter Width:")
label_width.pack(fill=tk.X, pady=5)
entry_width = ttk.Entry(frame, textvariable=obj2)
entry_width.pack(fill=tk.X, padx=20, pady=5)

label_height = ttk.Label(frame, text="Enter Height:")
label_height.pack(fill=tk.X, pady=5)
entry_height = ttk.Entry(frame, textvariable=obj3)
entry_height.pack(fill=tk.X, padx=20, pady=5)

btn_capture = ttk.Button(frame, text="Capture Screenshot", command=capture_screenshot)
btn_capture.pack(pady=10)

label_status = ttk.Label(frame, text="")
label_status.pack()

root.mainloop()
