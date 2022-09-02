#!/usr/bin/env python
# vi:sw=2:ts=2:sts=2:expandtab

from __future__ import print_function
import sys
import select
import time

# How many miliseconds to wait for the receiving application to retrieve the
# clipboard contents before taking ownership again for the next value. This is
# a hack, but AFAIK there is no way to know when the clipboard transaction has
# completed like there is in the X protocol, so this will have to do:
clipboard_hold_ms = 20

# We are currently using a hack to keep pumping the urwid main loop and polling
# stdin for keyboard input from a windows timer while we are processing the
# clipboard window's message queue. This controls how responsive the console
# will be, at the cost of wasting CPU time:
console_poll_ms = 20

# How many seconds to ignore clipboard requests after taking ownership of
# the clipboard. Intended to filter out things like clipboard managers and
# remote desktop applications that always want to know what's in the clipboard
# messing up our auto clipboard progression and that we likely don't want to
# give any credentials to anyway. Since Windows doesn't give us a way to know
# who's asking for the clipboard we can't explicitly blacklist these apps, but
# this seems to be the behaviour they all have in common. If it is actually
# intended to hand the credentials over to these use a capital yank instead.
ignore_clipboard_requests_within = 0.01

# Example of creating a window via ctypes (only necessary to take ownership of
# the clipboard to know when an application requests the contents. If we just
# wanted to set and forget the clipboard we wouldn't need to bother with this):
# https://gist.github.com/mouseroot/6128651

class ui_null(object):
  """
  Dummy class that will do nothing when called, and return itself as any of
  it's attributes.  Intended to be used in place of a ui class where no
  interaction is to take place. Calls such as ui_null().mainloop.foo.bar.baz()
  will not raise any exceptions.
  """
  def __call__(self, *args, **kwargs): pass
  def __getattribute__(self,name):
    return self

import ctypes
#from ctypes import * # More concise code, but less explicit

if sys.platform == 'cygwin':
  # To support running under cygwin we are conditionally replacing some
  # convenience helpers that are available for native windows python like
  # ctypes.windll, ctypes.wintypes, ctypes.WINFUNCTYPE, win32gui, etc.
  class wintypes(object):
    DWORD = ctypes.c_ulong
    HANDLE = ctypes.c_void_p # in the header files: void *
    HWND = HANDLE
    if ctypes.sizeof(ctypes.c_long) == ctypes.sizeof(ctypes.c_void_p):
        WPARAM = ctypes.c_ulong
        LPARAM = ctypes.c_long
    elif ctypes.sizeof(ctypes.c_longlong) == ctypes.sizeof(ctypes.c_void_p):
        WPARAM = ctypes.c_ulonglong
        LPARAM = ctypes.c_longlong
    LPCWSTR = LPWSTR = ctypes.c_wchar_p
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long),
                    ("y", ctypes.c_long)]
  class _wintypes(object):
    '''
    Anything that depends on the above types already being accessible in the
    wintypes namespace, since unlike modules the wintypes namespace isn't
    available in the middle of defining an enclosed class.
    '''
    class MSG(ctypes.Structure):
        _fields_ = [("hWnd", wintypes.HWND),
                    ("message", ctypes.c_uint),
                    ("wParam", wintypes.WPARAM),
                    ("lParam", wintypes.LPARAM),
                    ("time", wintypes.DWORD),
                    ("pt", wintypes.POINT)]
  wintypes.MSG = _wintypes.MSG
  del _wintypes

  _win_functype_cache = {}
  def WINFUNCTYPE(restype, *argtypes, **kw):
      _FUNCFLAG_STDCALL = 0 # XXX: Hardcoded this
      # docstring set later (very similar to CFUNCTYPE.__doc__)
      flags = _FUNCFLAG_STDCALL
      if kw.pop("use_errno", False):
          flags |= _FUNCFLAG_USE_ERRNO
      if kw.pop("use_last_error", False):
          flags |= _FUNCFLAG_USE_LASTERROR
      if kw:
          raise ValueError("unexpected keyword argument(s) %s" % kw.keys())
      try:
          return _win_functype_cache[(restype, argtypes, flags)]
      except KeyError:
          class WinFunctionType(ctypes._CFuncPtr):
              _argtypes_ = argtypes
              _restype_ = restype
              _flags_ = flags
          _win_functype_cache[(restype, argtypes, flags)] = WinFunctionType
          return WinFunctionType
  if WINFUNCTYPE.__doc__:
      WINFUNCTYPE.__doc__ = CFUNCTYPE.__doc__.replace("CFUNCTYPE", "WINFUNCTYPE")
  ctypes.WINFUNCTYPE = WINFUNCTYPE
  del WINFUNCTYPE
else:
  from ctypes import wintypes

class winmisc(object):
  '''
  Any additonal enums + structures we need that aren't found in wintypes
  '''
  WS_EX_APPWINDOW = 0x40000
  WS_OVERLAPPEDWINDOW = 0xcf0000
  WS_CAPTION = 0xc00000

  SW_SHOWNORMAL = 1
  SW_SHOW = 5

  CS_HREDRAW = 2
  CS_VREDRAW = 1

  CW_USEDEFAULT = 0x80000000

  WM_DESTROY = 2
  WM_TIMER = 0x0113
  WM_RENDERFORMAT = 0x0305
  WM_RENDERALLFORMATS = 0x0306
  WM_DESTROYCLIPBOARD = 0x0307
  WM_CLIPBOARDUPDATE = 0x031D

  WHITE_BRUSH = 0

  CF_TEXT = 1

  GMEM_MOVEABLE = 2

  class WNDCLASSEX(ctypes.Structure):
      WNDPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM)
      _fields_ = [("cbSize", ctypes.c_uint),
                  ("style", ctypes.c_uint),
                  ("lpfnWndProc", WNDPROCTYPE),
                  ("cbClsExtra", ctypes.c_int),
                  ("cbWndExtra", ctypes.c_int),
                  ("hInstance", wintypes.HANDLE),
                  ("hIcon", wintypes.HANDLE),
                  ("hCursor", wintypes.HANDLE),
                  ("hBrush", wintypes.HANDLE),
                  ("lpszMenuName", wintypes.LPCWSTR),
                  ("lpszClassName", wintypes.LPCWSTR),
                  ("hIconSm", wintypes.HANDLE)]

try:
  # Native windows python needs to use the right calling conventions
  user32 = ctypes.windll.user32
  kernel32 = ctypes.windll.kernel32
  #gdi32 = ctypes.windll.gdi32
except AttributeError:
  # Cygwin lacks the above, but seems happy with this:
  user32 = ctypes.CDLL("user32.dll")
  kernel32 = ctypes.CDLL("kernel32.dll")
  #gdi32 = ctypes.CDLL("gdi32.dll")


def defer_clipboard_copy(hWnd, formats=[winmisc.CF_TEXT]):
  rc = user32.OpenClipboard(hWnd)
  if not rc:
    return False
  user32.EmptyClipboard()
  for fmt in formats:
    user32.SetClipboardData(fmt, None)
  user32.CloseClipboard()
  return True

def copy_text_deferred(blob):
  text = bytes(blob) + b'\0' # blob may be utf8

  handle = kernel32.GlobalAlloc(winmisc.GMEM_MOVEABLE, len(text))
  buf = kernel32.GlobalLock(handle)
  ctypes.memmove(buf, text, len(text))
  kernel32.GlobalUnlock(handle)

  user32.SetClipboardData(winmisc.CF_TEXT, handle)
  user32.CloseClipboard()

def copy_text_simple(blob, hWnd=None):
  '''
  Simple copy text implementation that does not require an owning window, but
  will not be notified when an application requests the clipboard contents.
  '''
  rc = user32.OpenClipboard(hWnd)
  if not rc:
    return False
  user32.EmptyClipboard()
  copy_text_deferred(blob)

def empty_clipboard(ui, hWnd=None):
  user32.OpenClipboard(hWnd)
  user32.EmptyClipboard()
  user32.CloseClipboard()
  ui.status('Clipboard Cleared', append=True)

class ClipboardWindow(object):
  CLASS_NAME = 'kosh'
  def __init__(self, blobs, record=None, ui=ui_null()):
    self.blobs = iter(blobs)
    self.blob = next(self.blobs)
    self.record = record
    self.ui = ui
    self.clipboard_open_time = 0

    self.WndProc = winmisc.WNDCLASSEX.WNDPROCTYPE(self.PyWndProcedure)

    hInst = kernel32.GetModuleHandleW(0)
    wname = 'kosh'

    wndClass = winmisc.WNDCLASSEX()
    wndClass.cbSize = ctypes.sizeof(winmisc.WNDCLASSEX)
    wndClass.style = winmisc.CS_HREDRAW | winmisc.CS_VREDRAW
    wndClass.lpfnWndProc = self.WndProc
    wndClass.cbClsExtra = 0
    wndClass.cbWndExtra = 0
    wndClass.hInstance = hInst
    wndClass.hIcon = 0
    wndClass.hCursor = 0
    wndClass.hBrush = 0 #gdi32.GetStockObject(winmisc.WHITE_BRUSH)
    wndClass.lpszMenuName = 0
    wndClass.lpszClassName = self.CLASS_NAME
    wndClass.hIconSm = 0

    regRes = user32.RegisterClassExW(ctypes.byref(wndClass))

    self.hWnd = user32.CreateWindowExA(
      0,self.CLASS_NAME,wname,
      0, #winmisc.WS_OVERLAPPEDWINDOW | winmisc.WS_CAPTION,
      winmisc.CW_USEDEFAULT, winmisc.CW_USEDEFAULT,
      0,0,0,0,hInst,0)

    if not self.hWnd:
      print('Failed to create window')
      return
    #print('ShowWindow', user32.ShowWindow(self.hWnd, winmisc.SW_SHOW))
    #print('UpdateWindow', user32.UpdateWindow(self.hWnd))

    # Register for notifications of clipboard updates to determine when another
    # application takes clipboard ownership away from us:
    user32.AddClipboardFormatListener(self.hWnd)
    self.take_clipboard_ownership()

    # HACK: Timer to pump the urwid message queue and process stdin
    user32.SetTimer(self.hWnd, 1, console_poll_ms, None)

  def close(self):
    hInst = kernel32.GetModuleHandleW(0)
    user32.UnregisterClassA(self.CLASS_NAME, hInst)
    self.hWnd = None

  def take_clipboard_ownership(self):
    self.ui.status("Ready to send %s for '%s' via clipboard... (enter skips, escape cancels)" %
        (self.blob[0].upper(), self.record), append=True)
    defer_clipboard_copy(self.hWnd)
    self.clipboard_open_time = time.time()
    self.pump_tty_ui_main_loop()

  def pump_tty_ui_main_loop(self):
    # This is a hack to redraw the screen - we really should
    # restructure all this so as not to block instead:
    ui_fds = self.ui.mainloop.screen.get_input_descriptors()
    if ui_fds is None: ui_fds = []
    select_fds = set(ui_fds)
    if not select_fds: return

    self.ui.mainloop.draw_screen()
    while True:
      try:
        (readable, ign, ign) = select.select(select_fds, [], [], 0.0)
      except select.error as e:
        if e.args[0] == 4: continue # Interrupted system call
        raise
      break

    for fd in readable:
      if fd == sys.stdin.fileno():
        char = sys.stdin.read(1)
        if char == '\n':
          self.next()
        elif char == '\x1b':
          empty_clipboard(self.ui, self.hWnd)
          user32.DestroyWindow(self.hWnd)
      elif fd in ui_fds:
        self.ui.mainloop.event_loop._loop()

  def next(self):
    try:
      self.blob = next(self.blobs)
    except StopIteration:
      empty_clipboard(self.ui, self.hWnd)
      user32.DestroyWindow(self.hWnd)
      return False
    self.take_clipboard_ownership()
    return True

  def PyWndProcedure(self, hWnd, Msg, wParam, lParam):
    if Msg == winmisc.WM_DESTROY:
      user32.PostQuitMessage(0)
    elif Msg in (winmisc.WM_RENDERFORMAT, winmisc.WM_RENDERALLFORMATS):
      delta = time.time() - self.clipboard_open_time
      if delta < ignore_clipboard_requests_within:
        self.ui.status('Ignoring clipboard request within %.1fms of taking clipboard' % (delta*1000.0), append=True)
      else:
        copy_text_deferred(self.blob[1])
        user32.SetTimer(hWnd, 0, clipboard_hold_ms, None)
    elif Msg == winmisc.WM_TIMER:
      if wParam == 0:
        user32.KillTimer(hWnd, 0)
        self.next()
      elif wParam == 1:
        # FIXME: This is a hack to pump urwid main loop and process stdin
        self.pump_tty_ui_main_loop()
    elif Msg == winmisc.WM_DESTROYCLIPBOARD:
      # Seems useless since it only notifies me if I am the owner?
      if user32.GetClipboardOwner() != hWnd:
        self.ui.status('Lost control of clipboard (notified via WM_DESTROYCLIPBOARD)')
        user32.DestroyWindow(hWnd)
    elif Msg == winmisc.WM_CLIPBOARDUPDATE:
      if user32.GetClipboardOwner() != hWnd:
        self.ui.status('Lost control of clipboard')
        user32.DestroyWindow(hWnd)
    else:
      return user32.DefWindowProcW(hWnd, Msg, wParam, lParam)
    return 0

  def main_loop(self):
    # TODO: Respond to select() loop as well for enter/escape. For now we are
    # using a hack to periodically pump the urwid and stdin file descriptors
    # from a Windows timer.
    #
    # Note that Windows associates the window message queues with the thread
    # that created the window, so if we want to move this queue to another
    # thread we have to move the entire window to the same thread.
    msg = wintypes.MSG()
    lpmsg = ctypes.pointer(msg)

    while user32.GetMessageA(lpmsg, 0, 0, 0) != 0:
      user32.TranslateMessage(lpmsg)
      user32.DispatchMessageA(lpmsg)

    self.close()

def sendViaClipboardSimple(blobs, record = None, ui=ui_null()):
  def tty_ui_loop(ui):
    # FIXME: This works in cygwin, but might be problematic under native
    # Windows Python where select() only works on sockets
    ui_fds = ui.mainloop.screen.get_input_descriptors()
    if ui_fds is None: ui_fds = []
    select_fds = set(ui_fds)

    #old = ui_tty.set_cbreak() # Set unbuffered IO (if not already)
    try:
      while 1:
        ui.mainloop.draw_screen()
        while True:
          try:
            timeout = None
            (readable, ign, ign) = select.select(select_fds, [], [], timeout)
          except select.error as e:
            if e.args[0] == 4: continue # Interrupted system call
            raise
          break

        if not readable:
          break

        for fd in readable:
          if fd == sys.stdin.fileno():
            char = sys.stdin.read(1)
            if char == '\n':
              return True
            elif char == '\x1b':
              return False
          elif fd in ui_fds:
            # This is a hack to redraw the screen - we really should
            # restructure all this so as not to block instead:
            ui.mainloop.event_loop._loop()
    finally:
      pass
      #ui_tty.restore_cbreak(old)
  ui.status('')
  for (field, blob) in blobs:
    copy_text_simple(blob)
    ui.status("Copied %s for '%s' to clipboard, press enter to continue..."%(field.upper(),record), append=True)
    if not tty_ui_loop(ui):
      break
  empty_clipboard(ui)

def sendViaClipboard(blobs, record = None, ui=ui_null()):
  ui.status('')
  #old = ui_tty.set_cbreak() # Set unbuffered IO (if not already)
  try:
    clip_win = ClipboardWindow(blobs, record=record, ui=ui)
    clip_win.main_loop()
  except StopIteration:
    ui.status('Nothing to copy')
    # Ensure user won't paste previous clipboard contents into a login box if
    # they don't notice the message:
    empty_clipboard(ui)
  finally:
    pass
    #ui_tty.restore_cbreak(old)

if __name__ == '__main__':
  args = sys.argv[1:] if sys.argv[1:] else ['usage: ' , sys.argv[0], ' { strings }']
  blobs = zip([ "Item %i"%x for x in range(len(args)) ], args)
  sendViaClipboard(blobs, ui=ui_tty())
