# Screen Recorder - Copyright (C) 2026 TuanPA <tuanpa1702@gmail.com>
# SPDX-License-Identifier: GPL-3.0-only
# This program is free software under the GNU GPL v3; see LICENSE. It comes WITHOUT ANY WARRANTY.
"""VI/EN: Vietnamese source strings are the keys."""
import re

LANG = "vi"

EN = {
    "Gốc (giữ nguyên)": "Original (no scaling)", "Rất cao": "Very high", "Cao": "High", "Trung bình": "Medium",
    "Thấp (file nhỏ)": "Low (small file)",
    "Kéo chuột để chọn vùng quay  •  Esc để huỷ": "Drag to select the recording area  •  Esc to cancel",
    "Hiện cửa sổ": "Show window", "Bắt đầu / Dừng (F12)": "Start / Stop (F12)", "Thoát": "Exit",
    "Vùng quay": "Capture area", "Toàn màn hình": "Full screen", "Vùng chọn": "Region", "Cửa sổ": "Window",
    " Chọn vùng…": " Select region…", "Chưa chọn vùng": "No region selected", "Kích thước nhanh…": "Quick size…",
    "1080×1920 (dọc)": "1080×1920 (portrait)",
    "Làm mới danh sách cửa sổ": "Refresh window list", "Màn hình": "Monitor",
    "MKV (an toàn khi mất điện)": "MKV (safe on power loss)", "Quay con trỏ chuột": "Record mouse cursor",
    "Đếm ngược 3 giây": "3-second countdown", "Thu nhỏ cửa sổ khi quay": "Minimize window while recording",
    "Độ phân giải": "Resolution", "Khung hình": "Frame rate", "Chất lượng": "Quality", "Bộ mã hoá": "Encoder",
    "Định dạng": "Format", "Âm thanh": "Audio", "Âm thanh hệ thống": "System audio", "Lưu vào": "Save to",
    " Chọn…": " Browse…", " Mở thư mục": " Open folder", "Sẵn sàng": "Ready", " Chụp": " Screenshot",
    "Chụp ảnh màn hình (F11)": "Take a screenshot (F11)", " Tạm dừng": " Pause",
    "Tạm dừng / tiếp tục (Shift+F12)": "Pause / resume (Shift+F12)", "Bắt đầu / dừng quay (F12)": "Start / stop recording (F12)",
    "Phím tắt:  F12 bắt đầu/dừng  •  Shift+F12 tạm dừng  •  F11 chụp ảnh":
        "Hotkeys:  F12 start/stop  •  Shift+F12 pause  •  F11 screenshot",
    "Không đọc được thiết bị âm thanh: ": "Cannot read audio devices: ", "Mặc định": "Default",
    "Chọn thư mục lưu": "Choose output folder", "Hãy chọn vùng quay trước.": "Please select a region first.",
    "Hãy chọn cửa sổ cần quay.": "Please choose a window to record.", "Cửa sổ đã đóng, hãy chọn lại.": "The window was closed, please choose again.",
    "Đã huỷ": "Cancelled", "  DỪNG": "  STOP", " Tiếp tục": " Resume", "Đang lưu file…": "Saving file…",
    "Đã lưu ": "Saved ", "Mở thư mục": "Open folder", "Đóng": "Close", "Lỗi khi lưu:\n": "Error while saving:\n",
    "📷 Đã chụp: ": "📷 Captured: ", "Đã chụp ": "Captured ", "Chụp lỗi: ": "Screenshot failed: ",
    "Đang quay": "Recording", "Tạm dừng": "Paused",
    "⚠ ffmpeg dừng bất thường (cửa sổ bị đóng / màn hình thay đổi?)": "⚠ ffmpeg stopped unexpectedly (window closed / display changed?)",
    "Đang quay. Dừng và lưu rồi thoát?": "Recording in progress. Stop, save and exit?", "Lưu và thoát": "Save and exit",
    "Huỷ": "Cancel", "Có": "Yes", "Không": "No",
    " Cài vào máy": " Install", " Gỡ cài đặt": " Uninstall", "Cài đặt vào máy": "Install on this PC",
    "Gỡ cài đặt": "Uninstall",
    "Cài Screen Recorder cho tài khoản này (không cần quyền admin)?\n\nVị trí: %LOCALAPPDATA%\\Programs\\Screen Recorder\nTạo lối tắt ở Start Menu và Desktop.":
        "Install Screen Recorder for this account (no admin needed)?\n\nLocation: %LOCALAPPDATA%\\Programs\\Screen Recorder\nCreates Start Menu and Desktop shortcuts.",
    "Cài đặt": "Install", "Đã cài đặt xong. Mở bản đã cài ngay bây giờ?": "Installed. Open the installed copy now?",
    "Gỡ Screen Recorder khỏi máy? (Video đã quay không bị xoá)": "Uninstall Screen Recorder? (Your recordings are kept)",
    "Gỡ": "Uninstall", "Đã gỡ cài đặt. Ứng dụng sẽ đóng.": "Uninstalled. The app will now close.",
    "Lỗi cài đặt:\n": "Install error:\n", "Chỉ cài được từ bản exe.": "Install works only from the exe build.",
    "Chuyển ngôn ngữ": "Switch language", "Micro": "Microphone",
    "Chụp ảnh màn hình": "Screenshot", "Mẹo sử dụng": "Tips", "Nhận diện": "Identify", "Phần mềm tự do": "Free software",
    "Giấy phép": "Licenses", "Mã nguồn": "Source code",
    "Hiện số thứ tự trên từng màn hình": "Show the number on each screen", "Tất cả màn hình": "All monitors", "Tự do": "Freeform", "Tự do (theo nét kéo chuột)": "Freeform (follows your drag)",
    "Khi chụp:  kéo chuột = chọn vùng  •  R / D / W / F = vùng / tự do / cửa sổ / toàn màn hình  •  "
    "Enter = chụp cả màn hình  •  Esc hoặc chuột phải = huỷ\n"
    "Trình chỉnh sửa:  V P H L A R E T N B C = công cụ  •  giữ Shift = vuông / thẳng góc  •  "
    "kéo ô vuông = co giãn, chấm tròn = xoay  •  Ctrl+Z / Ctrl+Y  •  Ctrl+C copy  •  Ctrl+S lưu  •  Ctrl+lăn chuột = phóng to":
        "While snipping:  drag = region  •  R / D / W / F = region / freeform / window / full screen  •  Enter = whole screen  •  "
        "Esc or right-click = cancel\nEditor:  V P H L A R E T N B C = tools  •  hold Shift = square / straight  •  "
        "drag squares = resize, round dot = rotate  •  Ctrl+Z / Ctrl+Y  •  Ctrl+C copy  •  Ctrl+S save  •  Ctrl+wheel = zoom", "Phím tắt đang tắt. Dùng nút Chụp ngay hoặc menu ở khay hệ thống.":
        "Hotkey is off. Use the Snip now button or the tray menu.",
    "Phím tắt:  F12 bắt đầu/dừng  •  Shift+F12 tạm dừng": "Hotkeys:  F12 start/stop  •  Shift+F12 pause",
    "chụp ảnh": "screenshot",
    "Tổ hợp này thay thế Snipping Tool của Windows khi Screen Recorder đang chạy.":
        "This combo replaces the Windows Snipping Tool while Screen Recorder is running.",
    "Nếu Windows vẫn mở Snipping Tool: Settings › Accessibility › Keyboard › tắt “Use the Print screen key to open screen capture”.":
        "If Windows still opens Snipping Tool: Settings › Accessibility › Keyboard › turn off “Use the Print screen key to open screen capture”.",
    "Không cài được phím tắt toàn cục trên máy này.": "Could not install the global hotkey on this PC.",
    "Đã copy vào bộ nhớ tạm – dán bằng Ctrl+V.": "Copied to clipboard – paste with Ctrl+V.",
    "Đã lưu: ": "Saved: ", "Chỉnh sửa": "Edit", "Lưu": "Save", "Đã chụp ảnh màn hình": "Screenshot captured",
    "Chụp ảnh": "Screenshot", "Quay video": "Record video", "Tắt phím tắt": "Hotkey off", "Không hẹn giờ": "No delay",
    "Vùng chữ nhật": "Rectangle", "Phím tắt": "Hotkey", "Chế độ mặc định": "Default mode", "Hẹn giờ": "Delay",
    "Sau khi chụp": "After capture", "Mở trình chỉnh sửa ảnh": "Open the image editor",
    "Tự động lưu ảnh vào thư mục bên dưới": "Automatically save to the folder below",
    "Hiện thông báo (ảnh luôn được copy vào bộ nhớ tạm)": "Show a notification (the image is always copied to the clipboard)",
    "Khởi động cùng Windows (chạy nền ở khay hệ thống để phím tắt luôn hoạt động)":
        "Start with Windows (runs in the tray so the hotkey always works)",
    "Chụp ngay": "Snip now", "Vùng": "Region", "Huỷ (Esc)": "Cancel (Esc)", "Chỉnh sửa ảnh chụp": "Edit screenshot",
    "Chọn / di chuyển": "Select / move", "Bút vẽ": "Pen", "Bút dạ quang": "Highlighter", "Đường thẳng": "Line",
    "Mũi tên": "Arrow", "Hình chữ nhật": "Rectangle", "Hình elip": "Ellipse", "Chữ": "Text",
    "Đánh số thứ tự": "Step number", "Làm mờ / che thông tin": "Blur / redact", "Cắt ảnh": "Crop",
    "Màu khác…": "More colors…", "Độ dày nét / cỡ chữ": "Stroke width / text size", "Không tô": "No fill",
    "Tô mờ": "Light fill", "Tô đặc": "Solid fill", "Tô nền cho hình chữ nhật / elip": "Fill for rectangle / ellipse",
    "Hoàn tác": "Undo", "Làm lại": "Redo", "Chụp mới": "New snip",
    "Lưu nhanh vào thư mục ảnh (Ctrl+S) • Shift+Ctrl+S: Lưu thành…": "Quick save to the screenshots folder (Ctrl+S) • Shift+Ctrl+S: Save as…",
    "Vừa khung": "Fit", "Chọn màu": "Choose color", "Đã copy vào bộ nhớ tạm": "Copied to clipboard",
    "Lưu ảnh": "Save image", "Không lưu được: ": "Could not save: ", "Chụp ảnh màn hình ": "Screenshot ",
    "Screen Recorder vẫn chạy ở khay hệ thống để phím tắt chụp ảnh hoạt động. Chuột phải biểu tượng › Thoát để tắt hẳn.":
        "Screen Recorder keeps running in the tray so the snip hotkey works. Right-click the icon › Exit to quit.", "Đã cài đặt": "Installed",
}

PATTERNS = [
    (r"^v(.+) • Quay màn hình & chụp ảnh$", r"v\1 • Screen recording & screenshots"),
    (r"^Màn hình (\d+)( \(chính\))? — (.+)$", lambda m: f"Monitor {m[1]}{' (primary)' if m[2] else ''} — {m[3]}"),
    (r"^Tất cả màn hình — (.+)$", r"All monitors — \1"),
    (r"^Nhấn (.+) ở bất cứ đâu để chụp\. App cần đang chạy \(cửa sổ đóng thì vẫn chạy ở khay hệ thống\)\.$",
     r"Press \1 anywhere to snip. The app must be running (closing the window keeps it in the tray)."),
    (r"^Hẹn giờ (\d+) giây$", r"\1-second delay"),
    (r"^Vùng: (\S+) tại (.+)$", r"Region: \1 at \2"),
    (r"^Bắt đầu quay sau (\d+)s$", r"Recording starts in \1s"),
    (r"^Không bắt đầu quay được:\n", "Could not start recording:\n"),
    (r"^(.+) - đang quay$", r"\1 - recording"),
    (r"^✔ Đã lưu: ", "✔ Saved: "),
    (r"^\n⚠ Âm thanh: ", "\n⚠ Audio: "),
    (r"^Đã lưu video:\n(.+)\n\nMở thư mục chứa file\?$", lambda m: f"Video saved:\n{m[1]}\n\nOpen the containing folder?"),
]
PATTERNS = [(re.compile(p, re.S), r) for p, r in PATTERNS]


def T(s):
    if LANG != "en" or not isinstance(s, str):
        return s
    if s in EN:
        return EN[s]
    for p, r in PATTERNS:
        if p.search(s):
            return p.sub(r, s, count=1)
    return s
