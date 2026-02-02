# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('src/.env', '.'), ('resources', 'resources'), ('music', 'music'), ('src', 'src')],
    hiddenimports=['arcade', 'arcade.gui', 'arcade.gui.widgets', 'arcade.gui.elements', 'arcade.gui.style', 'edge_tts', 'groq', 'python_dotenv', 'pyglet', 'pymunk', 'pyglet.media.drivers.directsound', 'pyglet.media.drivers.xaudio2', 'pyglet.media.codecs.ffmpeg', 'pyglet.media.codecs.wmf', 'pyglet.font.freetype', 'pyglet.image.codecs.dds', 'pyglet.image.codecs.png', 'pyglet.image.codecs.jpg', 'pillow', 'PIL', 'numpy', 'numpy.core._dtype_ctypes', 'numpy.lib.format', 'asyncio.windows_events', 'multiprocessing', 'multiprocessing.pool', 'multiprocessing.spawn', 'aiohttp', 'aiohttp.client_reqrep', 'aiohttp.connector', 'aiohttp.resolver', 'charset_normalizer', 'urllib3', 'requests', 'ssl', 'certifi', 'websockets', 'uvloop', 'httpx'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('v', None, 'OPTION')],
    name='The Edges Of House',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources\\logo.ico'],
)
