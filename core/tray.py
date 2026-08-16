"""macOS 系统托盘(NSStatusItem via pyobjc)——pywebview 6 已移除内置 Tray"""
import objc
from AppKit import (NSObject, NSStatusBar, NSVariableStatusItemLength,
                    NSMenu, NSMenuItem)

class TrayHandler(NSObject):
    def init(self):
        self = objc.super(TrayHandler, self).init()
        self.status_item = None
        self.on_show = None
        self.on_quit = None
        return self

    @objc.python_method
    def setup(self, on_show, on_quit, title="📡"):
        """在 GUI 主线程调用"""
        self.on_show = on_show
        self.on_quit = on_quit
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength)
        self.status_item.setTitle_(title)
        menu = NSMenu.alloc().init()
        show_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "显示 LioDesktop", "showClicked:", "")
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出", "quitClicked:", "")
        show_item.setTarget_(self)
        quit_item.setTarget_(self)
        menu.addItem_(show_item)
        menu.addItem_(quit_item)
        self.status_item.setMenu_(menu)

    @objc.python_method
    def showClicked_(self, sender):
        if self.on_show:
            self.on_show()

    @objc.python_method
    def quitClicked_(self, sender):
        if self.on_quit:
            self.on_quit()
