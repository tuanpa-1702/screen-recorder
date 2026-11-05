# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""Recording engine: ffmpeg gdigrab (video) + soundcard WASAPI (system audio / mic).

Pause = end the current video segment; audio writers simply skip samples while
paused. On stop, segments are concatenated and muxed with the audio tracks.
"""
import ctypes, ctypes.wintypes as wt, os, subprocess, sys, threading, time, wave, shutil, tempfile

CREATE_NO_WINDOW = 0x08000000
SR = 48000


def ffmpeg_exe():
    base = getattr(sys, "_MEIPASS", None)
    if base and os.path.exists(os.path.join(base, "ffmpeg.exe")):
        return os.path.join(base, "ffmpeg.exe")
    here = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "ffmpeg.exe")
    if os.path.exists(here):
        return here
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def run_ff(args, **kw):
    return subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error"] + args,
                          creationflags=CREATE_NO_WINDOW, capture_output=True, **kw)


ENCODERS = [("libx264", "H.264 (CPU)"), ("h264_nvenc", "H.264 NVIDIA NVENC"),
            ("h264_qsv", "H.264 Intel QuickSync"), ("h264_amf", "H.264 AMD AMF"),
            ("libx265", "H.265/HEVC (CPU)"), ("hevc_nvenc", "H.265 NVIDIA NVENC")]


def available_encoders():
    ok = []
    for enc, label in ENCODERS:
        r = run_ff(["-f", "lavfi", "-i", "color=black:s=256x256:d=0.1", "-frames:v", "1",
                    "-c:v", enc, "-f", "null", "-"], timeout=20)
        if r.returncode == 0:
            ok.append((enc, label))
    return ok or ENCODERS[:1]


# ---------------- monitors / windows (physical pixels) ----------------
class MONITORINFOEX(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT),
                ("dwFlags", wt.DWORD), ("szDevice", wt.WCHAR * 32)]


def monitors():
    """[{name, x, y, w, h, primary}] in physical virtual-desktop coordinates."""
    out = []
    user32 = ctypes.windll.user32
    PROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)

    def cb(hmon, hdc, rc, lp):
        mi = MONITORINFOEX(); mi.cbSize = ctypes.sizeof(mi)
        user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        r = mi.rcMonitor
        out.append(dict(name=mi.szDevice, x=r.left, y=r.top, w=r.right - r.left,
                        h=r.bottom - r.top, primary=bool(mi.dwFlags & 1)))
        return True
    user32.EnumDisplayMonitors(None, None, PROC(cb), 0)
    out.sort(key=lambda m: (not m["primary"], m["x"], m["y"]))
    return out


def windows():
    """Visible top-level windows: [(title, hwnd)]"""
    user32 = ctypes.windll.user32
    res = []
    PROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(h, lp):
        if not user32.IsWindowVisible(h) or user32.IsIconic(h):
            return True
        n = user32.GetWindowTextLengthW(h)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(h, buf, n + 1)
        t = buf.value
        if t not in ("Program Manager", "Windows Input Experience") and t not in [x[0] for x in res]:
            res.append((t, h))
        return True
    user32.EnumWindows(PROC(cb), 0)
    return res


def window_rect(hwnd):
    r = wt.RECT()
    # DWMWA_EXTENDED_FRAME_BOUNDS = 9 (excludes invisible resize borders)
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
        ctypes.windll.user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def audio_devices():
    import pyaudiowpatch as pa
    p = pa.PyAudio()
    try:
        w = p.get_host_api_info_by_type(pa.paWASAPI)["index"]
        spk, mic = [], []
        for i in range(p.get_device_count()):
            d = p.get_device_info_by_index(i)
            if d["hostApi"] != w:
                continue
            if d["maxOutputChannels"] > 0:
                spk.append(d["name"])
            elif d["maxInputChannels"] > 0 and not d.get("isLoopbackDevice"):
                mic.append(d["name"])
        return spk, mic
    finally:
        p.terminate()


# ---------------- audio ----------------
class AudioTrack(threading.Thread):
    def __init__(self, kind, device_name, path, rec):
        super().__init__(daemon=True)
        self.kind, self.device_name, self.path, self.rec = kind, device_name, path, rec
        self.error = None
        self.level = 0.0
        self.paths = []
        self._stop = threading.Event()

    def _device(self, p):
        import pyaudiowpatch as pa
        if self.kind == "system":
            d = p.get_default_wasapi_loopback()
            for x in p.get_loopback_device_info_generator():
                if self.device_name and x["name"].startswith(self.device_name):
                    d = x
            return d
        w = p.get_host_api_info_by_type(pa.paWASAPI)
        d = p.get_device_info_by_index(w["defaultInputDevice"])
        for i in range(p.get_device_count()):
            x = p.get_device_info_by_index(i)
            if (x["hostApi"] == w["index"] and x["maxInputChannels"] > 0 and not x.get("isLoopbackDevice")
                    and x["name"] == self.device_name):
                d = x
        return d

    def run(self):
        import queue
        import numpy as np          # imported lazily: saves ~1 s at app start
        import pyaudiowpatch as pa
        p = pa.PyAudio()
        stream = None
        try:
            d = self._device(p)
            rate = int(d["defaultSampleRate"])
            ch = max(1, min(2, int(d["maxInputChannels"])))
            q = queue.Queue()
            stream = p.open(format=pa.paInt16, channels=ch, rate=rate, input=True,
                            input_device_index=d["index"], frames_per_buffer=rate // 50,
                            stream_callback=lambda data, n, ti, st: (q.put(data), (None, pa.paContinue))[1])
            self.rec.audio_ready.set()
            wf = None
            seg = -1
            fb = 2 * ch
            last = time.perf_counter()
            while not self._stop.is_set():
                time.sleep(0.03)
                now = time.perf_counter()
                recording = self.rec.state == "recording"
                if recording and seg != len(self.rec.segments) - 1:
                    # new video segment -> new wav (fitted to that segment's length on mux)
                    if wf:
                        wf.close()
                    seg = len(self.rec.segments) - 1
                    p_ = f"{self.path}.{seg:03d}.wav"
                    self.paths.append(p_)
                    wf = wave.open(p_, "wb")
                    wf.setnchannels(ch); wf.setsampwidth(2); wf.setframerate(rate)
                    written, rec_t = 0, 0.0
                if recording:
                    rec_t += now - last
                last = now
                chunks = []
                while not q.empty():
                    chunks.append(q.get_nowait())
                buf = b"".join(chunks)
                if buf:
                    a = np.frombuffer(buf, "<i2")
                    self.level = float(np.abs(a).max()) / 32767
                else:
                    self.level = 0.0
                if not recording or not wf:
                    continue
                wf.writeframes(buf); written += len(buf) // fb
                # loopback delivers nothing while the PC is silent -> pad with silence to keep A/V sync
                target = int(rec_t * rate)
                if written < target - rate // 10:
                    wf.writeframes(b"\0" * ((target - written) * fb)); written = target
            if wf:
                wf.close()
        except Exception as e:
            self.error = str(e)
            self.rec.audio_ready.set()
        finally:
            try:
                if stream:
                    stream.stop_stream(); stream.close()
            finally:
                p.terminate()

    def stop(self):
        self._stop.set()


def seg_duration(path):
    import re
    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-loglevel", "info", "-stats", "-i", path,
                        "-map", "0:v", "-c", "copy", "-f", "null", "-"],
                       creationflags=CREATE_NO_WINDOW, capture_output=True)
    t = re.findall(rb"time=(\d+):(\d+):([\d.]+)", r.stderr) or re.findall(rb"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    if not t:
        return 0.0
    h, m, s = t[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


# ---------------- recorder ----------------
class Recorder:
    """cfg keys: mode('monitor'|'region'|'window'), rect(x,y,w,h) physical, window_title,
    fps, height(0=original), encoder, quality(crf 15..35), fmt('mp4'|'mkv'), cursor(bool),
    sys_audio(bool), sys_dev, mic(bool), mic_dev, out_path"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.state = "idle"
        self.tmp = tempfile.mkdtemp(prefix="screenrec_")
        self.segments = []
        self.proc = None
        self.tracks = []
        self.audio_ready = threading.Event()
        self.t_acc = 0.0
        self.t_start = 0.0
        self.last_error = ""

    # elapsed recorded time (without pauses)
    def elapsed(self):
        return self.t_acc + (time.perf_counter() - self.t_start if self.state == "recording" else 0)

    def _video_args(self):
        c = self.cfg
        a = ["-y", "-f", "gdigrab", "-framerate", str(c["fps"]), "-draw_mouse", "1" if c["cursor"] else "0",
             "-thread_queue_size", "1024"]
        if c["mode"] == "window":
            a += ["-i", "title=" + c["window_title"]]
        else:
            x, y, w, h = c["rect"]
            w -= w % 2; h -= h % 2
            a += ["-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}", "-i", "desktop"]
        vf = []
        if c["height"]:
            vf.append(f"scale=-2:{c['height']}:flags=lanczos")
        else:
            vf.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
        enc = c["encoder"]
        if enc in ("h264_qsv",):
            vf.append("format=nv12")
        else:
            vf.append("format=yuv420p")
        a += ["-vf", ",".join(vf), "-c:v", enc]
        q = str(c["quality"])
        if enc in ("libx264", "libx265"):
            a += ["-preset", "veryfast" if c["fps"] <= 30 else "ultrafast", "-crf", q]
        elif "nvenc" in enc:
            a += ["-preset", "p4", "-rc", "vbr", "-cq", q, "-b:v", "0"]
        elif enc == "h264_qsv":
            a += ["-global_quality", q]
        elif enc == "h264_amf":
            a += ["-rc", "cqp", "-qp_i", q, "-qp_p", q]
        a += ["-fps_mode", "cfr", "-r", str(c["fps"])]
        return a

    def _start_segment(self):
        seg = os.path.join(self.tmp, f"seg{len(self.segments):03d}.mkv")
        self.segments.append(seg)
        cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error"] + self._video_args() + [seg]
        self.log = open(seg + ".log", "wb")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=self.log, stderr=self.log,
                                     creationflags=CREATE_NO_WINDOW)
        self.state = "recording"   # audio starts together with the ffmpeg process
        time.sleep(0.3)
        if self.proc.poll() is not None:
            self.log.close()
            raise RuntimeError("ffmpeg lỗi: " + open(seg + ".log", encoding="utf-8", errors="replace").read()[-800:])
        self.t_start = time.perf_counter()
        self.state = "recording"

    def _end_segment(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.write(b"q"); self.proc.stdin.flush()
            except Exception:
                pass
            try:
                self.proc.wait(15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.proc:
            self.log.close()
        self.proc = None

    def start(self):
        c = self.cfg
        if c.get("sys_audio"):
            self.tracks.append(AudioTrack("system", c.get("sys_dev"), os.path.join(self.tmp, "sys.wav"), self))
        if c.get("mic"):
            self.tracks.append(AudioTrack("mic", c.get("mic_dev"), os.path.join(self.tmp, "mic.wav"), self))
        for t in self.tracks:
            self.audio_ready.clear(); t.start(); self.audio_ready.wait(5)
        self._start_segment()

    def pause(self):
        if self.state != "recording":
            return
        self.state = "paused"
        self.t_acc += time.perf_counter() - self.t_start
        self._end_segment()

    def resume(self):
        if self.state == "paused":
            self._start_segment()

    def stop(self):
        """Stop and build the final file. Returns output path. Blocking (run in a thread)."""
        if self.state == "recording":
            self.t_acc += time.perf_counter() - self.t_start
        self.state = "stopping"
        self._end_segment()
        for t in self.tracks:
            t.stop()
        for t in self.tracks:
            t.join(5)
        out = self.cfg["out_path"]
        segs = [s for s in self.segments if os.path.exists(s) and os.path.getsize(s) > 0]
        if not segs:
            raise RuntimeError("Không có dữ liệu video được ghi.")
        lst = os.path.join(self.tmp, "list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for s in segs:
                f.write("file '" + s.replace("\\", "/").replace("'", "'\\''") + "'\n")
        args = ["-y", "-f", "concat", "-safe", "0", "-i", lst]
        durs = [seg_duration(s) for s in segs]
        tracks = [t for t in self.tracks if not t.error and len(t.paths) >= len(segs)]
        fc, outs, n = [], [], 1
        for ti, t in enumerate(tracks):
            parts = []
            for si, d in enumerate(durs):
                args += ["-i", t.paths[si]]
                # fit each audio piece exactly to its video segment -> no drift across pauses
                fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{d:.3f},asetpts=N/SR/TB[t{ti}s{si}]")
                parts.append(f"[t{ti}s{si}]"); n += 1
            fc.append("".join(parts) + f"concat=n={len(parts)}:v=0:a=1[t{ti}]")
            outs.append(f"[t{ti}]")
        auds = outs
        if len(outs) == 2:
            fc.append("[t0][t1]amix=inputs=2:duration=longest:normalize=0[a]")
        elif len(outs) == 1:
            fc.append("[t0]anull[a]")
        args += ["-map", "0:v"]
        if fc:
            args += ["-filter_complex", ";".join(fc), "-map", "[a]"]
        args += ["-c:v", "copy"]
        if auds:
            args += ["-c:a", "aac", "-b:a", "192k"]
        if out.lower().endswith(".mp4"):
            args += ["-movflags", "+faststart"]
        os.makedirs(os.path.dirname(out), exist_ok=True)
        r = run_ff(args + [out])
        if r.returncode != 0:
            raise RuntimeError("Ghép file lỗi: " + r.stderr.decode("utf-8", "replace")[-800:])
        errs = [f"{t.kind}: {t.error}" for t in self.tracks if t.error]
        self.last_error = "; ".join(errs)
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.state = "idle"
        return out
