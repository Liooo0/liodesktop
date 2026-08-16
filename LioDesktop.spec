# -*- mode: python ; coding: utf-8 -*-
# LioDesktop 正式打包 spec(标准 bundle,非 onefile)
# 用法: pyinstaller LioDesktop.spec
from PyInstaller.utils.hooks import collect_all

# pywebview + pyobjc 全量收集(macOS 后端依赖)
_datas_pw, _bin_pw, _hid_pw = collect_all('pywebview')
_datas_po, _bin_po, _hid_po = collect_all('pyobjc')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=_bin_pw + _bin_po,
    datas=[('ui', 'ui')] + _datas_pw + _datas_po,
    hiddenimports=[
        'core.server', 'core.logger', 'core.config', 'core.db',
        'core.service_manager', 'core.tray',
        'adapters.base', 'adapters.github_radar', 'adapters.model_radar',
        'adapters.llm',
        'waitress', 'flask',
    ] + _hid_pw + _hid_po,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LioDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='LioDesktop',
)
app = BUNDLE(
    coll,
    name='LioDesktop.app',
    icon=None,
    bundle_identifier='com.lio.liodesktop',
)
