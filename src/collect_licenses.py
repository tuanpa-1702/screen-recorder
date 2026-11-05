# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Gather license texts of everything shipped inside the exe into .\\licenses (bundled by build.bat)."""
import os, shutil, site, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "licenses")
SP = site.getusersitepackages()


def sp(*p):
    for base in [SP] + site.getsitepackages():
        f = os.path.join(base, *p)
        if os.path.exists(f):
            return f
    return None


PORTAUDIO = """PortAudio Portable Real-Time Audio Library
Copyright (c) 1999-2011 Ross Bencina and Phil Burk

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

FILES = [
    ("Screen-Recorder_GPL-3.0.txt", os.path.join(HERE, "licenses_src", "GPL-3.0.txt")),
    ("FFmpeg_GPL-3.0.txt", os.path.join(HERE, "licenses_src", "GPL-3.0.txt")),
    ("Qt_PySide6_LGPL-3.0.txt", os.path.join(HERE, "licenses_src", "LGPL-3.0.txt")),
    ("Qt_PySide6_GPL-3.0.txt", os.path.join(HERE, "licenses_src", "GPL-3.0.txt")),
    ("PyAudioWPatch_Apache-2.0.txt", sp("pyaudiowpatch-0.2.12.9.dist-info", "licenses", "LICENSE.txt")),
    ("numpy_BSD-3-Clause.txt", sp("numpy-2.5.4.dist-info", "licenses", "LICENSE.txt")),
    ("imageio-ffmpeg_BSD-2-Clause.txt", sp("imageio_ffmpeg-0.8.1.dist-info", "licenses", "LICENSE")),
    ("pywin32_PSF.txt", sp("win32", "License.txt")),
    ("PyInstaller_GPL-2.0-with-exception.txt", sp("pyinstaller-6.21.0.dist-info", "licenses", "COPYING.txt")),
    ("Python_PSF-2.0.txt", os.path.join(sys.base_prefix, "LICENSE.txt")),
]

NOTICE = """THIRD-PARTY SOFTWARE IN SCREEN RECORDER
=======================================

Screen Recorder (c) 2026 TuanPA - tuanpa1702@gmail.com
Licensed under the GNU General Public License v3.0 (see Screen-Recorder_GPL-3.0.txt).
Source code: https://github.com/tuanpa-1702/screen-recorder

The Windows executable bundles the following components, each under its own license:

Component        Version   License                      Use
---------------  --------  ---------------------------  ------------------------------------------
FFmpeg           9.0.2     GPL-3.0 (gyan.dev essentials  screen/video capture and encoding
                           build, --enable-gpl
                           --enable-version3, incl.
                           x264/x265)
Qt / PySide6     6.11.2    LGPL-3.0 (or GPL-3.0)        user interface
PyAudioWPatch    0.2.12.9  Apache-2.0                   WASAPI audio capture
PortAudio        19.x      MIT                          audio I/O (inside PyAudioWPatch)
numpy            2.5.4     BSD-3-Clause                 audio level / sample buffers
imageio-ffmpeg   0.8.1     BSD-2-Clause                 provides the FFmpeg binary at build time
pywin32          312       PSF                          shortcuts (Windows Script Host)
Python           3.13      PSF-2.0                      runtime
PyInstaller      6.21.0    GPL-2.0 + bootloader          packaging (the bootloader exception allows
                           exception                    distributing the built exe)

FFmpeg source code (GPL section 6):
  The bundled ffmpeg.exe is the unmodified "essentials" build 9.0.2 from https://www.gyan.dev/ffmpeg/builds/
  (shipped by the imageio-ffmpeg 0.8.1 wheel). Its complete corresponding source is available from
  https://ffmpeg.org/download.html (release 9.0.2) and the build scripts from https://www.gyan.dev/ffmpeg/builds/.
  For at least three years from distribution, a copy of that source can also be requested from
  tuanpa1702@gmail.com at no charge beyond the cost of physically providing it.

Qt / PySide6 (LGPL-3.0):
  Qt and PySide6 are used unmodified as dynamically linked libraries. You may replace them with your own
  compatible build: rebuild from source (https://github.com/tuanpa-1702/screen-recorder) or, in an installed
  copy, replace the DLLs in the _internal folder.
"""


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    missing = []
    for name, src in FILES:
        if src and os.path.exists(src):
            shutil.copyfile(src, os.path.join(OUT, name))
        else:
            missing.append(name)
    # PyAudioWPatch ships only its notice: append the full Apache-2.0 text
    with open(os.path.join(OUT, "PyAudioWPatch_Apache-2.0.txt"), "a", encoding="utf-8") as f:
        f.write("\n\n" + open(os.path.join(HERE, "licenses_src", "Apache-2.0.txt"), encoding="utf-8").read())
    with open(os.path.join(OUT, "PortAudio_MIT.txt"), "w", encoding="utf-8") as f:
        f.write(PORTAUDIO)
    with open(os.path.join(OUT, "THIRD_PARTY_NOTICES.txt"), "w", encoding="utf-8") as f:
        f.write(NOTICE)
    print("licenses ->", OUT, "| missing:", missing or "none")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
