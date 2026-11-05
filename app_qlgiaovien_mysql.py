import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from datetime import datetime, date

# Thư viện kết nối MySQL (cần cài: pip install mysql-connector-python)
try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

# Tự động nhận diện tkcalendar nếu máy có cài đặt
try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

# ==============================================================================
# CẤU HÌNH KẾT NỐI MySQL (MySQL Workbench / MySQL Server 8.0)
# ==============================================================================
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASS = "admin"          # Đổi thành mật khẩu MySQL Workbench của bạn (VD: admin, root, 123456 hoặc "")
DB_NAME = "qlgiaovien"

# ==============================================================================
# QUẢN LÝ PHIÊN ĐĂNG NHẬP & PHÂN QUYỀN (Mục 3.1.1 Báo cáo)
# ==============================================================================
TAI_KHOAN_MAU = {
    "admin":    {"matkhau": "123456", "vaitro": "Quản trị viên (Hiệu trưởng)", "quyen": "ALL"},
    "totruong": {"matkhau": "123456", "vaitro": "Tổ trưởng chuyên môn",        "quyen": "MANAGER"},
    "giaovien": {"matkhau": "123456", "vaitro": "Giáo viên",                   "quyen": "VIEW"},
}

CURRENT_USER = {
    "username": "admin",
    "vaitro": "Quản trị viên (Hiệu trưởng)",
    "quyen": "ALL",
    "so_lan_sai": 0,
    "bi_khoa": False
}

# ==============================================================================
# 1. HÀM KẾT NỐI & TỰ ĐỘNG KHỞI TẠO CSDL MySQL (4 BẢNG CHUẨN ERD HÌNH 3.2)
# ==============================================================================
def get_db_connection():
    """Trả về đối tượng kết nối MySQL. Trả về None nếu lỗi."""
    if not HAS_MYSQL:
        messagebox.showerror(
            "Thiếu thư viện",
            "Chưa cài đặt thư viện mysql-connector-python!\n\n"
            "Mở CMD / PowerShell và chạy lệnh:\n"
            "pip install mysql-connector-python tkcalendar"
        )
        return None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset="utf8mb4"
        )
        return conn
    except mysql.connector.Error as e:
        # Nếu chưa có database qlgiaovien thì tự động tạo database
        if getattr(e, "errno", None) == 1049:
            try:
                tmp_conn = mysql.connector.connect(
                    host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS
                )
                tmp_cur = tmp_conn.cursor()
                tmp_cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                tmp_conn.commit()
                tmp_cur.close()
                tmp_conn.close()
                return mysql.connector.connect(
                    host=DB_HOST, port=DB_PORT, user=DB_USER,
                    password=DB_PASS, database=DB_NAME, charset="utf8mb4"
                )
            except mysql.connector.Error as e2:
                e = e2

        messagebox.showerror(
            "Lỗi kết nối MySQL",
            f"Không thể kết nối cơ sở dữ liệu MySQL!\n\n"
            f"Chi tiết lỗi: {e}\n\n"
            f"Kiểm tra lại:\n"
            f"  1. Dịch vụ MySQL Server (MySQL80) đã khởi động chưa?\n"
            f"  2. Mật khẩu DB_PASS ('{DB_PASS}') trong code đã khớp với MySQL Workbench chưa?\n"
            f"  3. Đã chạy file 'sql_mysql.sql' trong MySQL Workbench chưa?"
        )
        return None


def init_db():
    """Khởi tạo 4 bảng chuẩn hóa (DM_ToChuyenMon, DM_ChucVu, HS_GiaoVien, QTr_KiemNhiem)."""
    conn = get_db_connection()
    if conn is None:
        return
    cur = conn.cursor()
    try:
        # 1. Bảng Danh mục Tổ chuyên môn
        cur.execute("""
            CREATE TABLE IF NOT EXISTS DM_ToChuyenMon (
                MaTo VARCHAR(10) PRIMARY KEY,
                TenTo VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # 2. Bảng Danh mục Chức vụ & Chế độ giảm trừ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS DM_ChucVu (
                MaCV VARCHAR(10) PRIMARY KEY,
                TenCV VARCHAR(100) NOT NULL,
                SoTietGiam INT DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # 3. Bảng Hồ sơ Giáo viên (có cột TrinhDo đúng sơ đồ ERD Hình 3.2)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS HS_GiaoVien (
                MaGV VARCHAR(20) PRIMARY KEY,
                HoTen VARCHAR(100) NOT NULL,
                GioiTinh VARCHAR(10),
                NgaySinh DATE,
                MaTo VARCHAR(10),
                TrinhDo VARCHAR(50),
                FOREIGN KEY (MaTo) REFERENCES DM_ToChuyenMon(MaTo) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Đảm bảo cột TrinhDo tồn tại nếu bảng HS_GiaoVien đã được tạo từ phiên bản cũ
        cur.execute("SHOW COLUMNS FROM HS_GiaoVien LIKE 'TrinhDo'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE HS_GiaoVien ADD COLUMN TrinhDo VARCHAR(50) DEFAULT 'Cử nhân Sư phạm'")

        # 4. Bảng Quá trình Kiêm nhiệm (Giải quyết quan hệ N-N)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS QTr_KiemNhiem (
                MaGV VARCHAR(20),
                MaCV VARCHAR(10),
                PRIMARY KEY (MaGV, MaCV),
                FOREIGN KEY (MaGV) REFERENCES HS_GiaoVien(MaGV) ON DELETE CASCADE,
                FOREIGN KEY (MaCV) REFERENCES DM_ChucVu(MaCV) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Nạp dữ liệu Tổ chuyên môn mẫu
        cur.executemany(
            "INSERT INTO DM_ToChuyenMon (MaTo, TenTo) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE TenTo=VALUES(TenTo)",
            [
                ('TOAN', 'Toán - Tin'),
                ('VAN',  'Ngữ Văn'),
                ('ANH',  'Ngoại Ngữ'),
                ('KHTN', 'Lý - Hóa - Sinh'),
                ('KHXH', 'Sử - Địa - GDCD'),
                ('VP',   'Tổ Văn phòng'),
            ]
        )

        # Nạp dữ liệu Chức vụ & Chế độ giảm trừ mẫu
        cur.executemany(
            "INSERT INTO DM_ChucVu (MaCV, TenCV, SoTietGiam) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE TenCV=VALUES(TenCV), SoTietGiam=VALUES(SoTietGiam)",
            [
                ('GV',  'Giáo viên bộ môn',               0),
                ('CN',  'Chủ nhiệm lớp',                  4),
                ('TT',  'Tổ trưởng chuyên môn',           3),
                ('TP',  'Tổ phó chuyên môn',              1),
                ('CD',  'Bí thư Đoàn',                    3),
                ('CON', 'Giáo viên nữ có con < 12 tháng', 3),
            ]
        )

        # Nạp dữ liệu Giáo viên mẫu nếu bảng rỗng
        cur.execute("SELECT COUNT(*) FROM HS_GiaoVien")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO HS_GiaoVien (MaGV, HoTen, GioiTinh, NgaySinh, MaTo, TrinhDo) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                [
                    ('GV001', 'Nguyễn Văn An',      'Nam', '1985-04-12', 'TOAN', 'Thạc sĩ'),
                    ('GV002', 'Trần Thị Bích Ngọc', 'Nữ',  '1992-11-20', 'VAN',  'Cử nhân Sư phạm'),
                    ('GV003', 'Lê Hoàng Minh',      'Nam', '1998-08-15', 'ANH',  'Cử nhân Sư phạm'),
                    ('GV004', 'Phạm Hồng Loan',     'Nữ',  '1988-01-30', 'KHTN', 'Thạc sĩ'),
                    ('GV005', 'Nguyễn Thị Lan',     'Nữ',  '1994-06-25', 'KHXH', 'Cử nhân Sư phạm'),
                ]
            )
            cur.executemany(
                "INSERT IGNORE INTO QTr_KiemNhiem (MaGV, MaCV) VALUES (%s, %s)",
                [
                    ('GV001', 'TT'),
                    ('GV002', 'CN'),
                    ('GV002', 'CON'),
                    ('GV003', 'CD'),
                    ('GV005', 'CN'),
                ]
            )

        conn.commit()
    except mysql.connector.Error as e:
        conn.rollback()
        messagebox.showerror("Lỗi khởi tạo CSDL", f"Lỗi khi khởi tạo bảng:\n{e}")
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 2. HÀM NGHIỆP VỤ TÍNH ĐỊNH MỨC GIỜ DẠY & KIÊM NHIỆM (Chuẩn 17 tiết/tuần)
# ==============================================================================
DINH_MUC_CHUAN = 17  # Định mức chuẩn giáo viên THPT công lập: 17 tiết/tuần


def lay_ds_to():
    """Lấy từ điển {MaTo: TenTo} từ CSDL."""
    ket_qua = {
        "TOAN": "Toán - Tin", "VAN": "Ngữ Văn", "ANH": "Ngoại Ngữ",
        "KHTN": "Lý - Hóa - Sinh", "KHXH": "Sử - Địa - GDCD", "VP": "Tổ Văn phòng"
    }
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT MaTo, TenTo FROM DM_ToChuyenMon")
            for mato, tento in cur.fetchall():
                ket_qua[mato] = tento
        except Exception:
            pass
        finally:
            cur.close()
            conn.close()
    return ket_qua


def lay_thong_tin_kiem_nhiem(conn, magv):
    """
    Trả về (chuoi_chuc_vu, so_tiet_giam, tiet_thuc_day) của 1 giáo viên
    dựa trên bảng QTr_KiemNhiem và DM_ChucVu.
    Quy tắc Bộ GD&ĐT: Nếu kiêm nhiệm nhiều chức vụ (tối đa 2), lấy mức giảm cao nhất.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT cv.TenCV, cv.SoTietGiam
        FROM QTr_KiemNhiem kn
        JOIN DM_ChucVu cv ON kn.MaCV = cv.MaCV
        WHERE kn.MaGV = %s
    """, (magv,))
    ds = cur.fetchall()
    cur.close()

    if not ds:
        return "Giáo viên bộ môn", 0, DINH_MUC_CHUAN

    ten_cac_cv = ", ".join([r[0] for r in ds])
    # Lấy số tiết giảm lớn nhất trong các chức vụ kiêm nhiệm
    so_tiet_giam = max([int(r[1] or 0) for r in ds])
    tiet_thuc_day = DINH_MUC_CHUAN - so_tiet_giam
    return ten_cac_cv, so_tiet_giam, tiet_thuc_day


def format_date_vn(ngaysinh):
    """Chuyển ngày YYYY-MM-DD sang DD/MM/YYYY để hiển thị chuẩn Việt Nam."""
    if not ngaysinh:
        return ""
    try:
        parts = str(ngaysinh).split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        pass
    return str(ngaysinh)


# ==============================================================================
# 3. HÀM XUẤT BÁO CÁO RA FILE EXCEL CSV (Thư viện csv chuẩn Chương 6)
# ==============================================================================
def xuat_excel(parent_win=None):
    file_path = filedialog.asksaveasfilename(
        parent=parent_win,
        defaultextension=".csv",
        filetypes=[("Tập tin Excel CSV (*.csv)", "*.csv"), ("Tất cả tập tin", "*.*")],
        initialfile="DanhSach_GiaoVien.csv",
        title="Lưu báo cáo danh sách giáo viên ra Excel"
    )
    if not file_path:
        return

    conn = get_db_connection()
    if conn is None:
        return

    try:
        to_map = lay_ds_to()
        cur = conn.cursor()
        cur.execute("SELECT MaGV, HoTen, GioiTinh, NgaySinh, MaTo, TrinhDo FROM HS_GiaoVien ORDER BY MaGV")
        rows = cur.fetchall()
        cur.close()

        # utf-8-sig giúp mở trực tiếp bằng Microsoft Excel không bị lỗi font tiếng Việt
        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Mã GV", "Họ và Tên", "Phái", "Ngày Sinh",
                "Tổ Chuyên Môn", "Trình Độ", "Chức Vụ / Kiêm Nhiệm",
                "Định Mức Chuẩn", "Số Tiết Giảm", "Tiết Thực Dạy/Tuần"
            ])
            for r in rows:
                magv, hoten, phai, ngaysinh, mato, trinhdo = r
                tento = to_map.get(mato, mato)
                td = trinhdo if trinhdo else "Cử nhân Sư phạm"
                cv_str, giam, day = lay_thong_tin_kiem_nhiem(conn, magv)
                ns_vn = format_date_vn(ngaysinh)
                writer.writerow([magv, hoten, phai, ns_vn, tento, td, cv_str, DINH_MUC_CHUAN, giam, day])

        conn.close()
        messagebox.showinfo(
            "Xuất báo cáo thành công",
            f"Đã kết xuất dữ liệu thành công ra tập tin:\n{file_path}\n\n"
            "(Mở trực tiếp bằng Microsoft Excel)",
            parent=parent_win
        )
    except Exception as e:
        conn.close()
        messagebox.showerror("Lỗi xuất file", f"Không thể xuất file Excel CSV:\n{e}", parent=parent_win)


# ==============================================================================
# 4. GIAO DIỆN CHÍNH (CỬA SỔ CHỦ THEO MẪU ẢNH CỦA THẦY MINH)
# ==============================================================================
root = tk.Tk()
root.title("Quản lý giáo viên")
root.geometry("820x540")
root.resizable(False, False)


def center_window(win, w=820, h=540):
    """Canh giữa cửa sổ trên màn hình."""
    ws = win.winfo_screenwidth()
    hs = win.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


center_window(root, 820, 540)

# Màn hình chính giới thiệu (Khớp ảnh bìa mẫu của Thầy Nguyễn Ngọc Minh)
frame_main_cover = tk.Frame(root, bg="#f5f5f5")
frame_main_cover.pack(fill="both", expand=True)

tk.Label(frame_main_cover, text="BÁO CÁO ĐỒ ÁN",
         font=("Arial", 22, "bold"), bg="#f5f5f5", fg="#111").pack(pady=(40, 5))
tk.Label(frame_main_cover, text="Chuyên đề Python (COS525)",
         font=("Arial", 18, "bold"), bg="#f5f5f5", fg="#222").pack(pady=(0, 20))

tk.Label(frame_main_cover, text="Đề tài: XÂY DỰNG ỨNG DỤNG QUẢN LÝ GIÁO VIÊN",
         font=("Arial", 16, "bold"), bg="#f5f5f5", fg="#0d47a1").pack()
tk.Label(frame_main_cover, text="VỚI PYTHON, TKINTER VÀ MySQL",
         font=("Arial", 16, "bold"), bg="#f5f5f5", fg="#0d47a1").pack(pady=(2, 30))

tk.Label(frame_main_cover, text="Giảng viên hướng dẫn",
         font=("Arial", 11, "italic"), bg="#f5f5f5").pack()
tk.Label(frame_main_cover, text="Ths. Nguyễn Ngọc Minh - Khoa CNTT - Trường ĐHAG",
         font=("Arial", 11, "bold"), bg="#f5f5f5").pack(pady=(2, 18))

tk.Label(frame_main_cover,
         text="Sinh viên thực hiện:    Nguyễn Huỳnh Nhựt Tân  -  MSSV: DTH245880",
         font=("Arial", 11), bg="#f5f5f5").pack(pady=2)
tk.Label(frame_main_cover,
         text="Sinh viên thực hiện:    Nguyễn Trọng Tín  -  MSSV: DTH245912",
         font=("Arial", 11), bg="#f5f5f5").pack(pady=2)

lbl_trangthai_user = tk.Label(
    frame_main_cover,
    text=f"Phiên đăng nhập: {CURRENT_USER['username']} — Vai trò: {CURRENT_USER['vaitro']}",
    font=("Arial", 10, "bold"), bg="#f5f5f5", fg="#1b5e20"
)
lbl_trangthai_user.pack(pady=(20, 4))

tk.Label(frame_main_cover, text="Cơ sở dữ liệu: MySQL (qlgiaovien) — Quản trị bằng MySQL Workbench",
         font=("Arial", 10, "italic"), bg="#f5f5f5", fg="#555").pack(pady=(2, 10))


def cap_nhat_nhan_user():
    if CURRENT_USER["username"]:
        lbl_trangthai_user.config(
            text=f"Phiên đăng nhập: {CURRENT_USER['username']} — Vai trò: {CURRENT_USER['vaitro']}",
            fg="#1b5e20"
        )
    else:
        lbl_trangthai_user.config(
            text="Trạng thái: Chưa đăng nhập (Vui lòng chọn Chương trình -> Đăng nhập)",
            fg="#c62828"
        )


def kiem_tra_quyen_ghi(parent_win):
    """Kiểm tra phân quyền trước khi Thêm/Sửa/Xóa."""
    if not CURRENT_USER["username"]:
        messagebox.showwarning("Chưa đăng nhập", "Vui lòng đăng nhập hệ thống trước khi thao tác!", parent=parent_win)
        return False
    if CURRENT_USER["quyen"] == "VIEW":
        messagebox.showwarning(
            "Phân quyền truy cập",
            f"Tài khoản '{CURRENT_USER['username']}' ({CURRENT_USER['vaitro']}) chỉ có quyền tra cứu và xem báo cáo!\n"
            "Chỉ Quản trị viên (Hiệu trưởng) hoặc Tổ trưởng mới có quyền cập nhật dữ liệu.",
            parent=parent_win
        )
        return False
    return True


# ==============================================================================
# 5. CỬA SỔ ĐĂNG NHẬP & PHÂN QUYỀN (Mục 3.1.1 - Khóa sau 5 lần nhập sai)
# ==============================================================================
def open_dangnhap():
    win = tk.Toplevel(root)
    win.title("Đăng nhập hệ thống")
    center_window(win, 420, 290)
    win.resizable(False, False)
    win.grab_set()
    win.focus_set()

    tk.Label(win, text="ĐĂNG NHẬP HỆ THỐNG", font=("Arial", 13, "bold"), fg="#0d47a1").pack(pady=(15, 5))
    tk.Label(win, text="(Tài khoản mẫu: admin / totruong / giaovien — Mật khẩu: 123456)",
             font=("Arial", 8, "italic"), fg="#555").pack(pady=(0, 10))

    f_form = tk.Frame(win, padx=20, pady=5)
    f_form.pack(fill="x")

    tk.Label(f_form, text="Tên đăng nhập:").grid(row=0, column=0, padx=5, pady=8, sticky="w")
    entry_user = ttk.Combobox(f_form, values=["admin", "totruong", "giaovien"], width=22)
    entry_user.set("admin")
    entry_user.grid(row=0, column=1, padx=5, pady=8, sticky="w")

    tk.Label(f_form, text="Mật khẩu:").grid(row=1, column=0, padx=5, pady=8, sticky="w")
    entry_pass = tk.Entry(f_form, width=25, show="*")
    entry_pass.insert(0, "123456")
    entry_pass.grid(row=1, column=1, padx=5, pady=8, sticky="w")

    lbl_canhbao = tk.Label(win, text="", font=("Arial", 9, "italic"), fg="#c62828")
    lbl_canhbao.pack(pady=4)

    def xu_ly_login():
        if CURRENT_USER["bi_khoa"]:
            messagebox.showerror(
                "Tài khoản bị khóa",
                "Tài khoản đã bị khóa tạm thời do nhập sai mật khẩu quá 5 lần!",
                parent=win
            )
            return

        u = entry_user.get().strip()
        p = entry_pass.get().strip()

        if u in TAI_KHOAN_MAU and TAI_KHOAN_MAU[u]["matkhau"] == p:
            CURRENT_USER["username"] = u
            CURRENT_USER["vaitro"] = TAI_KHOAN_MAU[u]["vaitro"]
            CURRENT_USER["quyen"] = TAI_KHOAN_MAU[u]["quyen"]
            CURRENT_USER["so_lan_sai"] = 0
            cap_nhat_nhan_user()
            messagebox.showinfo(
                "Đăng nhập thành công",
                f"Xin chào {u}!\nVai trò phân quyền: {CURRENT_USER['vaitro']}",
                parent=win
            )
            win.destroy()
        else:
            CURRENT_USER["so_lan_sai"] += 1
            con_lai = 5 - CURRENT_USER["so_lan_sai"]
            if CURRENT_USER["so_lan_sai"] >= 5:
                CURRENT_USER["bi_khoa"] = True
                btn_submit.config(state="disabled")
                lbl_canhbao.config(text="Đã khóa đăng nhập do nhập sai quá 5 lần!")
                messagebox.showerror(
                    "Khóa tài khoản",
                    "Bạn đã nhập sai mật khẩu 5 lần liên tiếp!\n"
                    "Hệ thống tự động khóa chức năng đăng nhập để bảo vệ dữ liệu.",
                    parent=win
                )
            else:
                lbl_canhbao.config(text=f"Sai mật khẩu! Còn {con_lai} lần thử trước khi khóa.")
                messagebox.showwarning(
                    "Sai thông tin",
                    f"Tên đăng nhập hoặc mật khẩu không đúng!\n(Số lần sai: {CURRENT_USER['so_lan_sai']}/5)",
                    parent=win
                )

    f_btn = tk.Frame(win)
    f_btn.pack(pady=10)
    btn_submit = tk.Button(f_btn, text="Đăng nhập", width=12, bg="#0d47a1", fg="white",
                           font=("Arial", 9, "bold"), command=xu_ly_login)
    btn_submit.pack(side="left", padx=6)
    tk.Button(f_btn, text="Đóng", width=10, command=win.destroy).pack(side="left", padx=6)

    if CURRENT_USER["bi_khoa"]:
        btn_submit.config(state="disabled")
        lbl_canhbao.config(text="Tài khoản đang bị khóa do nhập sai 5 lần!")


def xu_ly_dangxuat():
    if messagebox.askyesno("Đăng xuất", "Bạn có muốn đăng xuất khỏi phiên làm việc hiện tại?", parent=root):
        CURRENT_USER["username"] = ""
        CURRENT_USER["vaitro"] = "Chưa đăng nhập"
        CURRENT_USER["quyen"] = "NONE"
        cap_nhat_nhan_user()
        open_dangnhap()


# Cơ chế tự động đăng xuất sau 15 phút (900.000 ms) nhàn rỗi đúng Mục 3.1.1
IDLE_TIMEOUT_MS = 15 * 60 * 1000
_idle_timer_id = None


def _reset_idle_timer(event=None):
    global _idle_timer_id
    if _idle_timer_id is not None:
        root.after_cancel(_idle_timer_id)
    _idle_timer_id = root.after(IDLE_TIMEOUT_MS, _auto_logout_idle)


def _auto_logout_idle():
    if CURRENT_USER["username"]:
        CURRENT_USER["username"] = ""
        CURRENT_USER["vaitro"] = "Chưa đăng nhập"
        CURRENT_USER["quyen"] = "NONE"
        cap_nhat_nhan_user()
        messagebox.showinfo(
            "Tự động đăng xuất",
            "Phiên làm việc đã tự động đăng xuất sau 15 phút nhàn rỗi để bảo vệ dữ liệu!",
            parent=root
        )


root.bind_all("<Any-KeyPress>", _reset_idle_timer)
root.bind_all("<Any-ButtonPress>", _reset_idle_timer)
_reset_idle_timer()


# ==============================================================================
# 6. CÁC CỬA SỔ CHỨC NĂNG THEO MENU (CHẾ ĐỘ MODAL DIALOG)
# ==============================================================================

# --- CỬA SỔ 1: DANH MỤC -> NHÂN VIÊN / GIÁO VIÊN ---
def open_quanly_giaovien():
    win = tk.Toplevel(root)
    win.title("Danh mục Hồ sơ Giáo viên")
    center_window(win, 980, 620)
    win.grab_set()
    win.focus_set()

    to_map = lay_ds_to()
    rev_to_map = {v: k for k, v in to_map.items()}
    ds_ten_to = list(to_map.values())

    tk.Label(win, text="QUẢN LÝ HỒ SƠ GIÁO VIÊN THPT",
             font=("Arial", 14, "bold"), fg="#0d47a1").pack(pady=6)

    # Khung nhập liệu
    frame_info = tk.LabelFrame(win, text=" Thông tin hồ sơ giáo viên ",
                               font=("Arial", 9, "bold"), padx=10, pady=6)
    frame_info.pack(fill="x", padx=10, pady=4)

    tk.Label(frame_info, text="Mã GV (*):").grid(row=0, column=0, padx=5, pady=4, sticky="w")
    entry_magv = tk.Entry(frame_info, width=16)
    entry_magv.grid(row=0, column=1, padx=5, pady=4, sticky="w")

    tk.Label(frame_info, text="Họ và tên (*):").grid(row=0, column=2, padx=10, pady=4, sticky="w")
    entry_hoten = tk.Entry(frame_info, width=26)
    entry_hoten.grid(row=0, column=3, padx=5, pady=4, sticky="w")

    tk.Label(frame_info, text="Giới tính:").grid(row=0, column=4, padx=10, pady=4, sticky="w")
    gender_var = tk.StringVar(value="Nam")
    f_gender = tk.Frame(frame_info)
    f_gender.grid(row=0, column=5, padx=5, pady=4, sticky="w")
    tk.Radiobutton(f_gender, text="Nam", variable=gender_var, value="Nam").pack(side="left")
    tk.Radiobutton(f_gender, text="Nữ", variable=gender_var, value="Nữ").pack(side="left", padx=8)

    tk.Label(frame_info, text="Ngày sinh:").grid(row=1, column=0, padx=5, pady=4, sticky="w")
    if HAS_TKCALENDAR:
        date_entry = DateEntry(frame_info, width=14, background="darkblue",
                               foreground="white", date_pattern="dd/MM/yyyy")
        date_entry.grid(row=1, column=1, padx=5, pady=4, sticky="w")
    else:
        date_entry = tk.Entry(frame_info, width=16)
        date_entry.insert(0, "01/01/1990")
        date_entry.grid(row=1, column=1, padx=5, pady=4, sticky="w")

    tk.Label(frame_info, text="Tổ chuyên môn:").grid(row=1, column=2, padx=10, pady=4, sticky="w")
    cbb_to = ttk.Combobox(frame_info, values=ds_ten_to, width=24, state="readonly")
    if ds_ten_to:
        cbb_to.current(0)
    cbb_to.grid(row=1, column=3, padx=5, pady=4, sticky="w")

    tk.Label(frame_info, text="Trình độ:").grid(row=1, column=4, padx=10, pady=4, sticky="w")
    cbb_trinhdo = ttk.Combobox(
        frame_info,
        values=["Cử nhân Sư phạm", "Thạc sĩ", "Tiến sĩ", "Cao đẳng Sư phạm"],
        width=18, state="readonly"
    )
    cbb_trinhdo.current(0)
    cbb_trinhdo.grid(row=1, column=5, padx=5, pady=4, sticky="w")

    # Khung Tìm kiếm & Lọc theo Tổ (Khớp Hình 3.1 trong báo cáo)
    frame_search = tk.Frame(win, pady=4)
    frame_search.pack(fill="x", padx=10)

    tk.Label(frame_search, text="Tìm kiếm (Tên/Mã GV):").pack(side="left", padx=(0, 5))
    entry_timkiem = tk.Entry(frame_search, width=24)
    entry_timkiem.pack(side="left", padx=4)

    tk.Label(frame_search, text="Lọc theo Tổ:").pack(side="left", padx=(15, 5))
    cbb_loc_to = ttk.Combobox(frame_search, values=["-- Tất cả Tổ --"] + ds_ten_to, width=20, state="readonly")
    cbb_loc_to.current(0)
    cbb_loc_to.pack(side="left", padx=4)

    # Bảng Treeview
    frame_tree = tk.Frame(win)
    frame_tree.pack(fill="both", expand=True, padx=10, pady=4)

    cols = ("magv", "hoten", "phai", "ngaysinh", "to", "trinhdo", "chucvu", "giam", "day")
    tree = ttk.Treeview(frame_tree, columns=cols, show="headings", height=10)
    tree.heading("magv",     text="Mã GV")
    tree.heading("hoten",    text="Họ và Tên")
    tree.heading("phai",     text="Phái")
    tree.heading("ngaysinh", text="Ngày Sinh")
    tree.heading("to",       text="Tổ Chuyên Môn")
    tree.heading("trinhdo",  text="Trình Độ")
    tree.heading("chucvu",   text="Chức Vụ Kiêm Nhiệm")
    tree.heading("giam",     text="Giảm Trừ")
    tree.heading("day",      text="Định Mức Tiết")

    tree.column("magv",     width=65,  anchor="center")
    tree.column("hoten",    width=155)
    tree.column("phai",     width=50,  anchor="center")
    tree.column("ngaysinh", width=85,  anchor="center")
    tree.column("to",       width=115)
    tree.column("trinhdo",  width=115)
    tree.column("chucvu",   width=170)
    tree.column("giam",     width=70,  anchor="center")
    tree.column("day",      width=90,  anchor="center")

    sb = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    def load_data():
        for i in tree.get_children():
            tree.delete(i)
        conn = get_db_connection()
        if conn is None:
            return
        tu_khoa = entry_timkiem.get().strip().lower()
        ten_to_loc = cbb_loc_to.get()

        cur = conn.cursor()
        cur.execute("SELECT MaGV, HoTen, GioiTinh, NgaySinh, MaTo, TrinhDo FROM HS_GiaoVien ORDER BY MaGV")
        rows = cur.fetchall()
        cur.close()

        for row in rows:
            magv, hoten, phai, ngaysinh, mato, trinhdo = row
            tento = to_map.get(mato, mato)
            td = trinhdo if trinhdo else "Cử nhân Sư phạm"

            if tu_khoa and (tu_khoa not in magv.lower() and tu_khoa not in hoten.lower()):
                continue
            if ten_to_loc != "-- Tất cả Tổ --" and tento != ten_to_loc:
                continue

            cv_str, giam, day = lay_thong_tin_kiem_nhiem(conn, magv)
            ns_str = format_date_vn(ngaysinh)
            tree.insert("", tk.END, values=(
                magv, hoten, phai, ns_str, tento, td, cv_str, f"-{giam} tiết", f"{day} tiết"
            ))
        conn.close()

    tk.Button(frame_search, text="Tìm kiếm / Lọc", width=14, bg="#1976d2", fg="white",
              command=load_data).pack(side="left", padx=6)
    cbb_loc_to.bind("<<ComboboxSelected>>", lambda e: load_data())

    def clear_form():
        entry_magv.config(state="normal")
        entry_magv.delete(0, tk.END)
        entry_hoten.delete(0, tk.END)
        gender_var.set("Nam")
        if HAS_TKCALENDAR:
            try:
                date_entry.set_date(date(1995, 1, 1))
            except Exception:
                date_entry.set_date("01/01/1995")
        else:
            date_entry.delete(0, tk.END)
            date_entry.insert(0, "01/01/1995")
        if ds_ten_to:
            cbb_to.current(0)
        cbb_trinhdo.current(0)

    def _get_ngaysinh_mysql():
        raw = date_entry.get().strip()
        if not raw:
            return None
        parts = raw.replace("-", "/").split("/")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return f"{parts[0]}-{parts[1]}-{parts[2]}"
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return raw

    def them_gv():
        if not kiem_tra_quyen_ghi(win):
            return
        magv     = entry_magv.get().strip()
        hoten    = entry_hoten.get().strip()
        phai     = gender_var.get()
        ngaysinh = _get_ngaysinh_mysql()
        tento    = cbb_to.get()
        mato     = rev_to_map.get(tento, "TOAN")
        trinhdo  = cbb_trinhdo.get()

        if not magv or not hoten:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ Mã GV và Họ tên!", parent=win)
            return

        conn = get_db_connection()
        if conn is None:
            return
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO HS_GiaoVien (MaGV, HoTen, GioiTinh, NgaySinh, MaTo, TrinhDo) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (magv, hoten, phai, ngaysinh, mato, trinhdo)
            )
            conn.commit()
            messagebox.showinfo("Thành công", f"Đã thêm hồ sơ giáo viên: {hoten}", parent=win)
            load_data()
            clear_form()
        except mysql.connector.IntegrityError:
            conn.rollback()
            messagebox.showwarning("Trùng mã", f"Mã giáo viên '{magv}' đã tồn tại trong CSDL!", parent=win)
        finally:
            cur.close()
            conn.close()

    def chon_dong(event):
        sel = tree.selection()
        if not sel:
            return
        r = tree.item(sel[0])["values"]
        entry_magv.config(state="normal")
        entry_magv.delete(0, tk.END)
        entry_magv.insert(0, r[0])
        entry_magv.config(state="readonly")

        entry_hoten.delete(0, tk.END)
        entry_hoten.insert(0, r[1])
        gender_var.set(r[2])

        if HAS_TKCALENDAR:
            try:
                parts = str(r[3]).split("/")
                if len(parts) == 3:
                    date_entry.set_date(date(int(parts[2]), int(parts[1]), int(parts[0])))
                else:
                    date_entry.set_date(str(r[3]))
            except Exception:
                pass
        else:
            date_entry.delete(0, tk.END)
            date_entry.insert(0, str(r[3]))

        cbb_to.set(r[4])
        cbb_trinhdo.set(r[5])

    def sua_gv():
        if not kiem_tra_quyen_ghi(win):
            return
        magv = entry_magv.get().strip()
        if not magv:
            messagebox.showwarning("Cảnh báo", "Hãy chọn một giáo viên trong bảng để cập nhật!", parent=win)
            return
        hoten    = entry_hoten.get().strip()
        phai     = gender_var.get()
        ngaysinh = _get_ngaysinh_mysql()
        tento    = cbb_to.get()
        mato     = rev_to_map.get(tento, "TOAN")
        trinhdo  = cbb_trinhdo.get()

        conn = get_db_connection()
        if conn is None:
            return
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE HS_GiaoVien SET HoTen=%s, GioiTinh=%s, NgaySinh=%s, MaTo=%s, TrinhDo=%s "
                "WHERE MaGV=%s",
                (hoten, phai, ngaysinh, mato, trinhdo, magv)
            )
            conn.commit()
            messagebox.showinfo("Thành công", f"Đã cập nhật hồ sơ giáo viên {magv}", parent=win)
            load_data()
            clear_form()
        finally:
            cur.close()
            conn.close()

    def xoa_gv():
        if not kiem_tra_quyen_ghi(win):
            return
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Cảnh báo", "Hãy chọn giáo viên cần xóa!", parent=win)
            return
        r = tree.item(sel[0])["values"]
        if not messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc chắn muốn xóa hồ sơ giáo viên {r[1]} ({r[0]})?", parent=win):
            return
        conn = get_db_connection()
        if conn is None:
            return
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM HS_GiaoVien WHERE MaGV = %s", (r[0],))
            conn.commit()
            messagebox.showinfo("Thành công", "Đã xóa hồ sơ giáo viên!", parent=win)
            load_data()
            clear_form()
        finally:
            cur.close()
            conn.close()

    tree.bind("<<TreeviewSelect>>", chon_dong)

    # Cụm nút điều khiển
    f_btn = tk.Frame(win)
    f_btn.pack(pady=8)
    tk.Button(f_btn, text="Thêm",       width=9,  command=them_gv).grid(row=0, column=0, padx=4)
    tk.Button(f_btn, text="Lưu",        width=9,  command=sua_gv).grid(row=0, column=1, padx=4)
    tk.Button(f_btn, text="Sửa",        width=9,  command=sua_gv).grid(row=0, column=2, padx=4)
    tk.Button(f_btn, text="Hủy",        width=9,  command=clear_form).grid(row=0, column=3, padx=4)
    tk.Button(f_btn, text="Xóa",        width=9,  command=xoa_gv).grid(row=0, column=4, padx=4)
    tk.Button(f_btn, text="Phân công kiêm nhiệm", width=18, bg="#0d47a1", fg="white",
              font=("Arial", 9, "bold"),
              command=lambda: [win.destroy(), open_nghiepvu_dinhmuc()]).grid(row=0, column=5, padx=4)
    tk.Button(f_btn, text="Xuất Excel", width=11, bg="#27ae60", fg="white",
              font=("Arial", 9, "bold"), command=lambda: xuat_excel(win)).grid(row=0, column=6, padx=4)
    tk.Button(f_btn, text="Đóng",       width=9,  command=win.destroy).grid(row=0, column=7, padx=4)

    load_data()


# --- CỬA SỔ 2: DANH MỤC -> CHỨC VỤ & QUY ĐỊNH GIẢM TIẾT ---
def open_danhmuc_chucvu():
    win = tk.Toplevel(root)
    win.title("Danh mục Chức vụ & Chế độ giảm trừ")
    center_window(win, 680, 480)
    win.grab_set()
    win.focus_set()

    tk.Label(win, text="DANH MỤC CHỨC VỤ & QUY ĐỊNH GIẢM TIẾT",
             font=("Arial", 13, "bold"), fg="#0d47a1").pack(pady=8)

    f_form = tk.LabelFrame(win, text=" Thông tin chức vụ / chế độ giảm trừ ", padx=10, pady=6)
    f_form.pack(fill="x", padx=15, pady=4)

    tk.Label(f_form, text="Mã CV (*):").grid(row=0, column=0, padx=5, pady=4, sticky="w")
    e_macv = tk.Entry(f_form, width=12)
    e_macv.grid(row=0, column=1, padx=5, pady=4, sticky="w")

    tk.Label(f_form, text="Tên chức vụ (*):").grid(row=0, column=2, padx=8, pady=4, sticky="w")
    e_tencv = tk.Entry(f_form, width=25)
    e_tencv.grid(row=0, column=3, padx=5, pady=4, sticky="w")

    tk.Label(f_form, text="Số tiết giảm:").grid(row=0, column=4, padx=8, pady=4, sticky="w")
    e_giam = tk.Entry(f_form, width=8)
    e_giam.insert(0, "0")
    e_giam.grid(row=0, column=5, padx=5, pady=4, sticky="w")

    f_tree = tk.Frame(win)
    f_tree.pack(fill="both", expand=True, padx=15, pady=5)
    tree_cv = ttk.Treeview(f_tree, columns=("macv", "tencv", "giam"), show="headings", height=8)
    tree_cv.heading("macv",  text="Mã Chức Vụ")
    tree_cv.heading("tencv", text="Tên Chức Vụ / Chế Độ")
    tree_cv.heading("giam",  text="Số Tiết Giảm/Tuần")
    tree_cv.column("macv",  width=110, anchor="center")
    tree_cv.column("tencv", width=320)
    tree_cv.column("giam",  width=140, anchor="center")
    tree_cv.pack(fill="both", expand=True)

    def load_cv():
        for i in tree_cv.get_children():
            tree_cv.delete(i)
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT MaCV, TenCV, SoTietGiam FROM DM_ChucVu ORDER BY MaCV")
            for r in cur.fetchall():
                tree_cv.insert("", tk.END, values=r)
            cur.close()
            conn.close()

    def chon_cv(event):
        sel = tree_cv.selection()
        if not sel:
            return
        r = tree_cv.item(sel[0])["values"]
        e_macv.delete(0, tk.END)
        e_macv.insert(0, r[0])
        e_tencv.delete(0, tk.END)
        e_tencv.insert(0, r[1])
        e_giam.delete(0, tk.END)
        e_giam.insert(0, r[2])

    def luu_cv():
        if not kiem_tra_quyen_ghi(win):
            return
        macv = e_macv.get().strip().upper()
        tencv = e_tencv.get().strip()
        try:
            giam = int(e_giam.get().strip())
        except ValueError:
            messagebox.showwarning("Lỗi", "Số tiết giảm phải là số nguyên!", parent=win)
            return
        if not macv or not tencv:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Mã CV và Tên chức vụ!", parent=win)
            return
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO DM_ChucVu (MaCV, TenCV, SoTietGiam) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE TenCV=VALUES(TenCV), SoTietGiam=VALUES(SoTietGiam)",
                (macv, tencv, giam)
            )
            conn.commit()
            cur.close()
            conn.close()
            load_cv()
            messagebox.showinfo("Thành công", f"Đã lưu chức vụ '{tencv}'", parent=win)

    def xoa_cv():
        if not kiem_tra_quyen_ghi(win):
            return
        sel = tree_cv.selection()
        if not sel:
            return
        r = tree_cv.item(sel[0])["values"]
        if not messagebox.askyesno("Xác nhận", f"Xóa chức vụ {r[1]}?", parent=win):
            return
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM DM_ChucVu WHERE MaCV=%s", (r[0],))
            conn.commit()
            cur.close()
            conn.close()
            load_cv()

    tree_cv.bind("<<TreeviewSelect>>", chon_cv)

    f_btn = tk.Frame(win)
    f_btn.pack(pady=8)
    tk.Button(f_btn, text="Thêm / Lưu", width=12, command=luu_cv).pack(side="left", padx=5)
    tk.Button(f_btn, text="Xóa", width=10, command=xoa_cv).pack(side="left", padx=5)
    tk.Button(f_btn, text="Đóng", width=10, command=win.destroy).pack(side="left", padx=5)

    load_cv()


# --- CỬA SỔ 3: DANH MỤC -> TỔ BỘ MÔN / PHÒNG BAN ---
def open_danhmuc_phongban():
    win = tk.Toplevel(root)
    win.title("Danh mục Tổ chuyên môn / Phòng ban")
    center_window(win, 620, 440)
    win.grab_set()
    win.focus_set()

    tk.Label(win, text="DANH MỤC TỔ CHUYÊN MÔN & PHÒNG BAN",
             font=("Arial", 13, "bold"), fg="#0d47a1").pack(pady=8)

    f_form = tk.LabelFrame(win, text=" Thông tin Tổ chuyên môn ", padx=10, pady=6)
    f_form.pack(fill="x", padx=15, pady=4)

    tk.Label(f_form, text="Mã Tổ (*):").grid(row=0, column=0, padx=5, pady=4, sticky="w")
    e_mato = tk.Entry(f_form, width=14)
    e_mato.grid(row=0, column=1, padx=5, pady=4, sticky="w")

    tk.Label(f_form, text="Tên Tổ chuyên môn (*):").grid(row=0, column=2, padx=10, pady=4, sticky="w")
    e_tento = tk.Entry(f_form, width=28)
    e_tento.grid(row=0, column=3, padx=5, pady=4, sticky="w")

    f_tree = tk.Frame(win)
    f_tree.pack(fill="both", expand=True, padx=15, pady=5)
    tree_pb = ttk.Treeview(f_tree, columns=("mato", "tento"), show="headings", height=8)
    tree_pb.heading("mato",  text="Mã Tổ")
    tree_pb.heading("tento", text="Tên Tổ Chuyên Môn / Phòng Ban")
    tree_pb.column("mato",  width=150, anchor="center")
    tree_pb.column("tento", width=380)
    tree_pb.pack(fill="both", expand=True)

    def load_pb():
        for i in tree_pb.get_children():
            tree_pb.delete(i)
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT MaTo, TenTo FROM DM_ToChuyenMon ORDER BY MaTo")
            for r in cur.fetchall():
                tree_pb.insert("", tk.END, values=r)
            cur.close()
            conn.close()

    def chon_pb(event):
        sel = tree_pb.selection()
        if not sel:
            return
        r = tree_pb.item(sel[0])["values"]
        e_mato.delete(0, tk.END)
        e_mato.insert(0, r[0])
        e_tento.delete(0, tk.END)
        e_tento.insert(0, r[1])

    def luu_pb():
        if not kiem_tra_quyen_ghi(win):
            return
        mato = e_mato.get().strip().upper()
        tento = e_tento.get().strip()
        if not mato or not tento:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Mã Tổ và Tên Tổ!", parent=win)
            return
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO DM_ToChuyenMon (MaTo, TenTo) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE TenTo=VALUES(TenTo)",
                (mato, tento)
            )
            conn.commit()
            cur.close()
            conn.close()
            load_pb()
            messagebox.showinfo("Thành công", f"Đã lưu tổ '{tento}'", parent=win)

    def xoa_pb():
        if not kiem_tra_quyen_ghi(win):
            return
        sel = tree_pb.selection()
        if not sel:
            return
        r = tree_pb.item(sel[0])["values"]
        if not messagebox.askyesno("Xác nhận", f"Xóa tổ {r[1]}?", parent=win):
            return
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM DM_ToChuyenMon WHERE MaTo=%s", (r[0],))
            conn.commit()
            cur.close()
            conn.close()
            load_pb()

    tree_pb.bind("<<TreeviewSelect>>", chon_pb)

    f_btn = tk.Frame(win)
    f_btn.pack(pady=8)
    tk.Button(f_btn, text="Thêm / Lưu", width=12, command=luu_pb).pack(side="left", padx=5)
    tk.Button(f_btn, text="Xóa", width=10, command=xoa_pb).pack(side="left", padx=5)
    tk.Button(f_btn, text="Đóng", width=10, command=win.destroy).pack(side="left", padx=5)

    load_pb()


# --- CỬA SỔ 4: NGHIỆP VỤ -> PHÂN CÔNG KIÊM NHIỆM & TÍNH ĐỊNH MỨC GIỜ DẠY ---
def open_nghiepvu_dinhmuc():
    win = tk.Toplevel(root)
    win.title("Nghiệp vụ Phân công kiêm nhiệm & Tính định mức giảng dạy")
    center_window(win, 920, 560)
    win.grab_set()
    win.focus_set()

    tk.Label(win, text="PHÂN CÔNG KIÊM NHIỆM & BẢNG TỔNG HỢP ĐỊNH MỨC GIỜ DẠY",
             font=("Arial", 13, "bold"), fg="#0d47a1").pack(pady=(8, 2))
    tk.Label(
        win,
        text="Quy chuẩn Bộ GD&ĐT: Định mức chuẩn THPT = 17 tiết/tuần | Tối đa 02 chức vụ kiêm nhiệm/giáo viên (lấy mức giảm cao nhất)",
        font=("Arial", 9, "italic"), fg="#555"
    ).pack(pady=(0, 6))

    # Khung phân công kiêm nhiệm (Thao tác trực tiếp bảng QTr_KiemNhiem)
    f_assign = tk.LabelFrame(win, text=" Phân công kiêm nhiệm / Chế độ giảm trừ (Bảng QTr_KiemNhiem) ",
                             font=("Arial", 9, "bold"), padx=10, pady=6)
    f_assign.pack(fill="x", padx=15, pady=4)

    conn = get_db_connection()
    ds_gv = []
    ds_cv = []
    gv_gender_map = {}
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT MaGV, HoTen, GioiTinh FROM HS_GiaoVien ORDER BY MaGV")
        for mgv, ht, gt in cur.fetchall():
            ds_gv.append(f"{mgv} - {ht}")
            gv_gender_map[mgv] = gt
        cur.execute("SELECT MaCV, TenCV, SoTietGiam FROM DM_ChucVu WHERE MaCV != 'GV' ORDER BY MaCV")
        for mcv, tcv, giam in cur.fetchall():
            ds_cv.append(f"{mcv} - {tcv} (-{giam} tiết)")
        cur.close()
        conn.close()

    tk.Label(f_assign, text="Chọn Giáo viên:").grid(row=0, column=0, padx=5, pady=4, sticky="w")
    cbb_gv = ttk.Combobox(f_assign, values=ds_gv, width=30, state="readonly")
    if ds_gv:
        cbb_gv.current(0)
    cbb_gv.grid(row=0, column=1, padx=5, pady=4, sticky="w")

    tk.Label(f_assign, text="Chức vụ / Chế độ:").grid(row=0, column=2, padx=10, pady=4, sticky="w")
    cbb_cv = ttk.Combobox(f_assign, values=ds_cv, width=34, state="readonly")
    if ds_cv:
        cbb_cv.current(0)
    cbb_cv.grid(row=0, column=3, padx=5, pady=4, sticky="w")

    # Bảng tổng hợp định mức
    f_tree = tk.Frame(win)
    f_tree.pack(fill="both", expand=True, padx=15, pady=6)
    tree_nv = ttk.Treeview(
        f_tree,
        columns=("magv", "hoten", "to", "trinhdo", "chucvu", "tieuchuan", "giam", "thucday"),
        show="headings", height=10
    )
    tree_nv.heading("magv",      text="Mã GV")
    tree_nv.heading("hoten",     text="Họ và Tên")
    tree_nv.heading("to",        text="Tổ Chuyên Môn")
    tree_nv.heading("trinhdo",   text="Trình Độ")
    tree_nv.heading("chucvu",    text="Chức Vụ / Chế Độ Kiêm Nhiệm")
    tree_nv.heading("tieuchuan", text="Tiêu Chuẩn")
    tree_nv.heading("giam",      text="Giảm Trừ")
    tree_nv.heading("thucday",   text="Thực Dạy/Tuần")

    tree_nv.column("magv",      width=65,  anchor="center")
    tree_nv.column("hoten",     width=150)
    tree_nv.column("to",        width=110)
    tree_nv.column("trinhdo",   width=110)
    tree_nv.column("chucvu",    width=210)
    tree_nv.column("tieuchuan", width=75,  anchor="center")
    tree_nv.column("giam",      width=70,  anchor="center")
    tree_nv.column("thucday",   width=90,  anchor="center")

    sb = ttk.Scrollbar(f_tree, orient="vertical", command=tree_nv.yview)
    tree_nv.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    tree_nv.pack(fill="both", expand=True)

    def load_bang_dinh_muc():
        for i in tree_nv.get_children():
            tree_nv.delete(i)
        conn = get_db_connection()
        if not conn:
            return
        to_map = lay_ds_to()
        cur = conn.cursor()
        cur.execute("SELECT MaGV, HoTen, MaTo, TrinhDo FROM HS_GiaoVien ORDER BY MaGV")
        rows = cur.fetchall()
        cur.close()
        for magv, hoten, mato, trinhdo in rows:
            cv_str, giam, day = lay_thong_tin_kiem_nhiem(conn, magv)
            td = trinhdo if trinhdo else "Cử nhân Sư phạm"
            tree_nv.insert("", tk.END, values=(
                magv, hoten, to_map.get(mato, mato), td,
                cv_str, f"{DINH_MUC_CHUAN} tiết", f"-{giam} tiết", f"{day} tiết"
            ))
        conn.close()

    def them_kiem_nhiem():
        if not kiem_tra_quyen_ghi(win):
            return
        if not cbb_gv.get() or not cbb_cv.get():
            return
        magv = cbb_gv.get().split(" - ")[0].strip()
        macv = cbb_cv.get().split(" - ")[0].strip()

        # Kiểm tra điều kiện giới tính cho chế độ CON (< 12 tháng tuổi)
        if macv == "CON" and gv_gender_map.get(magv) == "Nam":
            messagebox.showwarning(
                "Vi phạm quy tắc nghiệp vụ",
                "Chế độ 'Giáo viên nữ có con < 12 tháng' chỉ áp dụng cho giáo viên Nữ!",
                parent=win
            )
            return

        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        try:
            # Thuật toán đếm COUNT trên bảng QTr_KiemNhiem (Mục 3.2.5 báo cáo): Tối đa 02 chức vụ
            cur.execute("SELECT COUNT(*) FROM QTr_KiemNhiem WHERE MaGV = %s", (magv,))
            so_luong = cur.fetchone()[0]
            if so_luong >= 2:
                messagebox.showwarning(
                    "Vượt quá giới hạn kiêm nhiệm",
                    f"Giáo viên {magv} hiện đã kiêm nhiệm {so_luong} chức vụ!\n"
                    "Theo quy định, mỗi giáo viên không được phân công kiêm nhiệm quá 02 chức vụ.",
                    parent=win
                )
                return

            cur.execute("INSERT INTO QTr_KiemNhiem (MaGV, MaCV) VALUES (%s, %s)", (magv, macv))
            conn.commit()
            load_bang_dinh_muc()
            messagebox.showinfo("Thành công", f"Đã phân công chức vụ '{macv}' cho giáo viên {magv}!", parent=win)
        except mysql.connector.IntegrityError:
            conn.rollback()
            messagebox.showwarning("Trùng phân công", f"Giáo viên {magv} đã có chức vụ '{macv}' rồi!", parent=win)
        finally:
            cur.close()
            conn.close()

    def xoa_kiem_nhiem():
        if not kiem_tra_quyen_ghi(win):
            return
        if not cbb_gv.get():
            return
        magv = cbb_gv.get().split(" - ")[0].strip()
        if not messagebox.askyesno("Xác nhận", f"Xóa toàn bộ chức vụ kiêm nhiệm của giáo viên {magv}?", parent=win):
            return
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM QTr_KiemNhiem WHERE MaGV = %s", (magv,))
            conn.commit()
            cur.close()
            conn.close()
            load_bang_dinh_muc()
            messagebox.showinfo("Đã xóa", f"Đã đưa giáo viên {magv} về định mức Giáo viên bộ môn (17 tiết).", parent=win)

    def chon_dong_nv(event):
        sel = tree_nv.selection()
        if not sel:
            return
        magv = tree_nv.item(sel[0])["values"][0]
        for item in ds_gv:
            if item.startswith(f"{magv} -"):
                cbb_gv.set(item)
                break

    tree_nv.bind("<<TreeviewSelect>>", chon_dong_nv)

    f_btn_assign = tk.Frame(f_assign)
    f_btn_assign.grid(row=1, column=0, columnspan=4, pady=6)
    tk.Button(f_btn_assign, text="Gán kiêm nhiệm", width=15, bg="#0d47a1", fg="white",
              font=("Arial", 9, "bold"), command=them_kiem_nhiem).pack(side="left", padx=5)
    tk.Button(f_btn_assign, text="Xóa kiêm nhiệm của GV", width=20,
              command=xoa_kiem_nhiem).pack(side="left", padx=5)

    f_action = tk.Frame(win)
    f_action.pack(pady=8)
    tk.Button(f_action, text="Xuất Báo Cáo Excel", width=18,
              bg="#27ae60", fg="white", font=("Arial", 9, "bold"),
              command=lambda: xuat_excel(win)).pack(side="left", padx=6)
    tk.Button(f_action, text="Đóng", width=10, command=win.destroy).pack(side="left", padx=6)

    load_bang_dinh_muc()


# --- BÁO CÁO ---
def open_baocao_ds():
    open_quanly_giaovien()


def open_baocao_tonghop():
    open_nghiepvu_dinhmuc()


# --- GIÚP ĐỠ ---
def show_huongdan():
    messagebox.showinfo(
        "Hướng dẫn sử dụng",
        "HƯỚNG DẪN SỬ DỤNG HỆ THỐNG:\n\n"
        "1. Chương trình → Đăng nhập / Đăng xuất (Tài khoản mẫu: admin / 123456).\n"
        "   Tự động khóa nếu nhập sai mật khẩu quá 5 lần.\n"
        "2. Danh mục → Nhân viên / Giáo viên: Thêm, Sửa, Xóa, Tìm kiếm, Lọc theo Tổ.\n"
        "3. Danh mục → Chức vụ / Phòng ban: Quản lý danh mục tổ và mức giảm trừ tiết.\n"
        "4. Nghiệp vụ → Phân công kiêm nhiệm & Định mức: Gán kiêm nhiệm (tối đa 02 chức vụ/GV) và tính tiết thực dạy tự động.\n"
        "5. Báo cáo → Xuất Excel: Xuất bảng tổng hợp ra tập tin CSV mở trực tiếp bằng Excel.",
        parent=root
    )


def show_thongtin():
    messagebox.showinfo(
        "Thông tin đồ án",
        "ĐỒ ÁN CHUYÊN ĐỀ PYTHON (COS525)\n"
        "Đề tài: Xây dựng ứng dụng Quản lý giáo viên phổ thông\n\n"
        "GVHD: ThS. Nguyễn Ngọc Minh\n"
        "Nhóm thực hiện:\n"
        "  - Nguyễn Huỳnh Nhựt Tân (DTH245880)\n"
        "  - Nguyễn Trọng Tín (DTH245912)\n"
        "Lớp: DH25TH3 - Nhóm 14 - Tổ 1\n"
        "Trường Đại học An Giang - ĐHQG-HCM",
        parent=root
    )


# ==============================================================================
# 7. MENU BAR (5 menu theo đúng ảnh mẫu của Thầy Nguyễn Ngọc Minh)
# ==============================================================================
menubar = tk.Menu(root)

# 1. Chương trình
menu_chuongtrinh = tk.Menu(menubar, tearoff=0)
menu_chuongtrinh.add_command(label="Đăng nhập / Đổi tài khoản", command=open_dangnhap)
menu_chuongtrinh.add_command(label="Đăng xuất",                 command=xu_ly_dangxuat)
menu_chuongtrinh.add_separator()
menu_chuongtrinh.add_command(label="Thoát",                     command=root.quit)
menubar.add_cascade(label="Chương trình", menu=menu_chuongtrinh)

# 2. Danh mục
menu_danhmuc = tk.Menu(menubar, tearoff=0)
menu_danhmuc.add_command(label="Nhân viên / Giáo viên",   command=open_quanly_giaovien)
menu_danhmuc.add_command(label="Chức vụ",                 command=open_danhmuc_chucvu)
menu_danhmuc.add_command(label="Phòng ban / Tổ bộ môn",   command=open_danhmuc_phongban)
menubar.add_cascade(label="Danh mục", menu=menu_danhmuc)

# 3. Nghiệp vụ
menu_nghiepvu = tk.Menu(menubar, tearoff=0)
menu_nghiepvu.add_command(label="Phân công kiêm nhiệm & Định mức (Quá trình lương)",
                          command=open_nghiepvu_dinhmuc)
menubar.add_cascade(label="Nghiệp vụ", menu=menu_nghiepvu)

# 4. Báo cáo
menu_baocao = tk.Menu(menubar, tearoff=0)
menu_baocao.add_command(label="Danh sách giáo viên",       command=open_baocao_ds)
menu_baocao.add_command(label="Tổng hợp định mức giờ dạy", command=open_baocao_tonghop)
menu_baocao.add_separator()
menu_baocao.add_command(label="Xuất danh sách ra Excel",   command=lambda: xuat_excel(root))
menubar.add_cascade(label="Báo cáo", menu=menu_baocao)

# 5. Giúp đỡ
menu_giupdo = tk.Menu(menubar, tearoff=0)
menu_giupdo.add_command(label="Hướng dẫn", command=show_huongdan)
menu_giupdo.add_command(label="Thông tin", command=show_thongtin)
menubar.add_cascade(label="Giúp đỡ", menu=menu_giupdo)

root.config(menu=menubar)

# ==============================================================================
# 8. KHỞI ĐỘNG HỆ THỐNG
# ==============================================================================
init_db()

root.mainloop()
