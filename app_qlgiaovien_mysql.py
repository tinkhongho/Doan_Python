import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import hashlib
from datetime import date

try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False


# CẤU HÌNH KẾT NỐI MySQL
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASS = "admin"          # Mật khẩu MySQL Workbench của bạn
DB_NAME = "qlgiaovien"

LOAI_TRUONG_MAP = {
    "THPT (17 tiết)":     17,
    "Nội trú (15 tiết)":  15,
    "THCS (19 tiết)":     19,
    "Tiểu học (23 tiết)": 23,
}
CURRENT_DINH_MUC = 17
MA_TIEN_TO = "GV"          


def ma_hoa_mk(mat_khau):
    """Mã hóa mk dạng Hash SHA-256"""
    return hashlib.sha256(mat_khau.encode("utf-8")).hexdigest()


# 1. KẾT NỐI, KHỞI TẠO CSDL MySQL
def get_db_connection():
    if not HAS_MYSQL:
        messagebox.showerror(
            "Thiếu thư viện",
            "Chưa cài mysql-connector-python!\nChạy lệnh: pip install mysql-connector-python tkcalendar"
        )
        return None
    try:
        return mysql.connector.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASS, database=DB_NAME, charset="utf8mb4"
        )
    except mysql.connector.Error as e:
        if getattr(e, "errno", None) == 1049:
            try:
                tmp = mysql.connector.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS)
                cur = tmp.cursor()
                cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                tmp.commit()
                cur.close()
                tmp.close()
                return mysql.connector.connect(
                    host=DB_HOST, port=DB_PORT, user=DB_USER,
                    password=DB_PASS, database=DB_NAME, charset="utf8mb4"
                )
            except mysql.connector.Error as e2:
                e = e2
        messagebox.showerror("Lỗi kết nối MySQL", f"Không thể kết nối MySQL:\n{e}")
        return None


def init_db():
    conn = get_db_connection()
    if conn is None:
        return
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS TaiKhoan (
                TenDangNhap VARCHAR(50) PRIMARY KEY,
                MatKhau VARCHAR(64) NOT NULL,
                Quyen VARCHAR(20) NOT NULL DEFAULT 'user'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS DM_ToChuyenMon (
                MaTo VARCHAR(10) PRIMARY KEY,
                TenTo VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS DM_ChucVu (
                MaCV VARCHAR(10) PRIMARY KEY,
                TenCV VARCHAR(100) NOT NULL,
                SoTietGiam INT DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS HS_GiaoVien (
                MaGV VARCHAR(20) PRIMARY KEY,
                HoTen VARCHAR(100) NOT NULL,
                GioiTinh VARCHAR(10),
                NgaySinh DATE,
                MaTo VARCHAR(10),
                TrinhDo VARCHAR(50),
                FOREIGN KEY (MaTo) REFERENCES DM_ToChuyenMon(MaTo) ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cur.execute("SHOW COLUMNS FROM HS_GiaoVien LIKE 'TrinhDo'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE HS_GiaoVien ADD COLUMN TrinhDo VARCHAR(50) DEFAULT 'Cử nhân Sư phạm'")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS QTr_KiemNhiem (
                MaGV VARCHAR(20),
                MaCV VARCHAR(10),
                PRIMARY KEY (MaGV, MaCV),
                FOREIGN KEY (MaGV) REFERENCES HS_GiaoVien(MaGV) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (MaCV) REFERENCES DM_ChucVu(MaCV) ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        mk_bam = ma_hoa_mk("123456")
        cur.executemany(
            "INSERT IGNORE INTO TaiKhoan (TenDangNhap, MatKhau, Quyen) VALUES (%s, %s, %s)",
            [
                ('admin', mk_bam, 'admin'),
                ('user',  mk_bam, 'user'),
                ('gv',    mk_bam, 'user'),
            ]
        )

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

        cur.executemany(
            "INSERT INTO DM_ChucVu (MaCV, TenCV, SoTietGiam) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE TenCV=VALUES(TenCV), SoTietGiam=VALUES(SoTietGiam)",
            [
                ('CN',  'Chủ nhiệm lớp',                 4),
                ('TT',  'Tổ trưởng chuyên môn',          3),
                ('TP',  'Tổ phó chuyên môn',             1),
                ('CD',  'Bí thư Đoàn',                   3),
                ('CON', 'Nữ có con nhỏ < 12 tháng',      3),
            ]
        )

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
        messagebox.showerror("Lỗi CSDL", f"Lỗi khởi tạo dữ liệu:\n{e}")
    finally:
        cur.close()
        conn.close()


# 2. HÀM XỬ LÝ NGHIỆP VỤ
def center_window(win, w, h):
    ws = win.winfo_screenwidth()
    hs = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(ws - w) // 2}+{(hs - h) // 2}")


def tach_tien_to_va_so(ma):
    ma = ma.strip().upper()
    i = 0
    while i < len(ma) and ma[i].isalpha():
        i += 1
    return ma[:i], ma[i:]


def lay_tien_to_hien_tai():
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT MaGV FROM HS_GiaoVien LIMIT 1")
            row = cur.fetchone()
            if row and row[0]:
                tt, _ = tach_tien_to_va_so(str(row[0]))
                if tt:
                    return tt
        finally:
            cur.close()
            conn.close()
    return "GV"


def lay_ds_to():
    ket_qua = {}
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT MaTo, TenTo FROM DM_ToChuyenMon ORDER BY MaTo")
            for mato, tento in cur.fetchall():
                ket_qua[mato] = tento
        finally:
            cur.close()
            conn.close()
    if not ket_qua:
        ket_qua = {"TOAN": "Toán - Tin", "VAN": "Ngữ Văn", "ANH": "Ngoại Ngữ"}
    return ket_qua


def lay_thong_tin_kiem_nhiem(conn, magv):
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
        return "Không", 0, CURRENT_DINH_MUC

    ten_cv = ", ".join([r[0] for r in ds])
    giam = max([int(r[1] or 0) for r in ds])
    thuc_day = max(0, CURRENT_DINH_MUC - giam)
    return ten_cv, giam, thuc_day


def format_date_vn(ngaysinh):
    if not ngaysinh:
        return ""
    parts = str(ngaysinh).split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return str(ngaysinh)


def xuat_excel(parent_win=None):
    file_path = filedialog.asksaveasfilename(
        parent=parent_win,
        defaultextension=".csv",
        filetypes=[("Excel CSV (*.csv)", "*.csv"), ("Tất cả tập tin", "*.*")],
        initialfile="DanhSach_GiaoVien.csv",
        title="Xuất danh sách giáo viên"
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

        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Mã GV", "Họ và Tên", "Giới Tính", "Ngày Sinh",
                "Tổ Chuyên Môn", "Trình Độ", "Kiêm Nhiệm",
                "Tiết Chuẩn", "Tiết Giảm", "Tiết Thực Dạy"
            ])
            for magv, hoten, phai, ngaysinh, mato, trinhdo in rows:
                tento = to_map.get(mato, mato)
                td = trinhdo if trinhdo else "Cử nhân Sư phạm"
                cv_str, giam, day = lay_thong_tin_kiem_nhiem(conn, magv)
                writer.writerow([
                    magv, hoten, phai, format_date_vn(ngaysinh),
                    tento, td, cv_str, CURRENT_DINH_MUC, giam, day
                ])
        conn.close()
        messagebox.showinfo("Thành công", f"Đã xuất file:\n{file_path}", parent=parent_win)
    except Exception as e:
        conn.close()
        messagebox.showerror("Lỗi", f"Không thể xuất file:\n{e}", parent=parent_win)


# 3. CỬA SỔ CHÍNH & CÁC CỬA SỔ NGHIỆP VỤ
def mo_man_hinh_chinh(role="admin", username="admin"):
    global CURRENT_DINH_MUC, MA_TIEN_TO, to_map, rev_to_map, ds_ten_to
    root = tk.Tk()
    ten_quyen = "Quản trị viên (Admin)" if role == "admin" else "Giáo viên (User - Chỉ xem)"
    root.title(f"Phần mềm Quản lý Giáo viên Phổ thông - [{username} | {ten_quyen}]")
    center_window(root, 980, 600)
    root.resizable(False, False)

    MA_TIEN_TO = lay_tien_to_hien_tai()
    to_map = lay_ds_to()
    rev_to_map = {v: k for k, v in to_map.items()}
    ds_ten_to = list(to_map.values())

    # CÁC CỬA SỔ CON: ĐỔI MẬT KHẨU, QUẢN LÝ TÀI KHOẢN, DANH MỤC TỔ, CHỨC VỤ
    def open_doi_mat_khau():
        win = tk.Toplevel(root)
        win.title("Đổi mật khẩu")
        center_window(win, 360, 210)
        win.grab_set()
        win.focus_set()

        f = tk.Frame(win, padx=16, pady=12)
        f.pack(fill="both", expand=True)

        tk.Label(f, text=f"Tài khoản: {username}", font=("Arial", 9, "bold"), fg="#0d47a1").grid(
            row=0, column=0, columnspan=2, pady=(0, 8), sticky="w"
        )

        tk.Label(f, text="Mật khẩu hiện tại:").grid(row=1, column=0, pady=4, sticky="w")
        e_cu = tk.Entry(f, width=20, show="*")
        e_cu.grid(row=1, column=1, pady=4, padx=6)

        tk.Label(f, text="Mật khẩu mới:").grid(row=2, column=0, pady=4, sticky="w")
        e_moi = tk.Entry(f, width=20, show="*")
        e_moi.grid(row=2, column=1, pady=4, padx=6)

        tk.Label(f, text="Nhập lại mật khẩu:").grid(row=3, column=0, pady=4, sticky="w")
        e_xn = tk.Entry(f, width=20, show="*")
        e_xn.grid(row=3, column=1, pady=4, padx=6)

        def luu_mk():
            mk_cu = e_cu.get().strip()
            mk_moi = e_moi.get().strip()
            mk_xn = e_xn.get().strip()
            if not mk_cu or not mk_moi or not mk_xn:
                messagebox.showwarning("Chú ý", "Vui lòng nhập đầy đủ các trường!", parent=win)
                return
            if mk_moi != mk_xn:
                messagebox.showwarning("Không khớp", "Mật khẩu mới nhập lại không khớp!", parent=win)
                return
            conn = get_db_connection()
            if not conn:
                return
            cur = conn.cursor()
            try:
                cur.execute("SELECT MatKhau FROM TaiKhoan WHERE TenDangNhap=%s", (username,))
                row = cur.fetchone()
                if not row or row[0] != ma_hoa_mk(mk_cu):
                    messagebox.showerror("Lỗi", "Mật khẩu hiện tại không đúng!", parent=win)
                    return
                cur.execute(
                    "UPDATE TaiKhoan SET MatKhau=%s WHERE TenDangNhap=%s",
                    (ma_hoa_mk(mk_moi), username)
                )
                conn.commit()
                messagebox.showinfo("Thành công", "Đã đổi mật khẩu thành công!", parent=win)
                win.destroy()
            finally:
                cur.close()
                conn.close()

        f_b = tk.Frame(f)
        f_b.grid(row=4, column=0, columnspan=2, pady=10)
        tk.Button(f_b, text="Lưu", width=10, command=luu_mk).pack(side="left", padx=4)
        tk.Button(f_b, text="Đóng", width=10, command=win.destroy).pack(side="left", padx=4)

    def open_quanly_taikhoan():
        win = tk.Toplevel(root)
        win.title("Quản lý tài khoản")
        center_window(win, 520, 380)
        win.grab_set()
        win.focus_set()

        f_form = tk.LabelFrame(win, text=" Thông tin tài khoản ", padx=10, pady=6)
        f_form.pack(fill="x", padx=12, pady=8)

        tk.Label(f_form, text="Tài khoản:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        e_tk = tk.Entry(f_form, width=14)
        e_tk.grid(row=0, column=1, padx=4, pady=4)

        tk.Label(f_form, text="Mật khẩu:").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        e_mk = tk.Entry(f_form, width=14, show="*")
        e_mk.grid(row=0, column=3, padx=4, pady=4)

        tk.Label(f_form, text="Quyền:").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        cbb_quyen = ttk.Combobox(f_form, values=["user", "admin"], width=8, state="readonly")
        cbb_quyen.current(0)
        cbb_quyen.grid(row=0, column=5, padx=4, pady=4)

        f_tree = tk.Frame(win)
        f_tree.pack(fill="both", expand=True, padx=12, pady=4)
        tree_tk = ttk.Treeview(f_tree, columns=("tk", "quyen"), show="headings", height=8)
        tree_tk.heading("tk", text="Tên Đăng Nhập")
        tree_tk.heading("quyen", text="Quyền Hạn")
        tree_tk.column("tk", width=260)
        tree_tk.column("quyen", width=180, anchor="center")
        tree_tk.pack(fill="both", expand=True)

        def load_tk():
            for i in tree_tk.get_children():
                tree_tk.delete(i)
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT TenDangNhap, Quyen FROM TaiKhoan ORDER BY TenDangNhap")
                for r in cur.fetchall():
                    tree_tk.insert("", tk.END, values=r)
                cur.close()
                conn.close()

        def chon_tk(event):
            sel = tree_tk.selection()
            if not sel:
                return
            r = tree_tk.item(sel[0])["values"]
            e_tk.delete(0, tk.END)
            e_tk.insert(0, r[0])
            cbb_quyen.set(r[1])
            e_mk.delete(0, tk.END)

        def luu_tk():
            tk_nhap = e_tk.get().strip()
            mk_nhap = e_mk.get().strip()
            quyen_nhap = cbb_quyen.get().strip()
            if not tk_nhap:
                messagebox.showwarning("Chú ý", "Vui lòng nhập Tên tài khoản!", parent=win)
                return
            conn = get_db_connection()
            if not conn:
                return
            cur = conn.cursor()
            try:
                cur.execute("SELECT TenDangNhap FROM TaiKhoan WHERE TenDangNhap=%s", (tk_nhap,))
                ton_tai = cur.fetchone()
                if ton_tai:
                    if mk_nhap:
                        cur.execute(
                            "UPDATE TaiKhoan SET MatKhau=%s, Quyen=%s WHERE TenDangNhap=%s",
                            (ma_hoa_mk(mk_nhap), quyen_nhap, tk_nhap)
                        )
                    else:
                        cur.execute(
                            "UPDATE TaiKhoan SET Quyen=%s WHERE TenDangNhap=%s",
                            (quyen_nhap, tk_nhap)
                        )
                else:
                    if not mk_nhap:
                        messagebox.showwarning("Chú ý", "Vui lòng nhập mật khẩu cho tài khoản mới!", parent=win)
                        return
                    cur.execute(
                        "INSERT INTO TaiKhoan (TenDangNhap, MatKhau, Quyen) VALUES (%s, %s, %s)",
                        (tk_nhap, ma_hoa_mk(mk_nhap), quyen_nhap)
                    )
                conn.commit()
                load_tk()
                e_mk.delete(0, tk.END)
                messagebox.showinfo("Thành công", f"Đã lưu tài khoản '{tk_nhap}'!", parent=win)
            finally:
                cur.close()
                conn.close()

        def xoa_tk():
            sel = tree_tk.selection()
            if not sel:
                return
            r = tree_tk.item(sel[0])["values"]
            if r[0] == username:
                messagebox.showwarning("Không thể xóa", "Không thể xóa tài khoản đang đăng nhập!", parent=win)
                return
            if not messagebox.askyesno("Xác nhận", f"Xóa tài khoản '{r[0]}'?", parent=win):
                return
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM TaiKhoan WHERE TenDangNhap=%s", (r[0],))
                conn.commit()
                cur.close()
                conn.close()
                load_tk()

        tree_tk.bind("<<TreeviewSelect>>", chon_tk)

        f_btn = tk.Frame(win)
        f_btn.pack(pady=8)
        tk.Button(f_btn, text="Lưu", width=10, command=luu_tk).pack(side="left", padx=4)
        tk.Button(f_btn, text="Xóa", width=10, command=xoa_tk).pack(side="left", padx=4)
        tk.Button(f_btn, text="Đóng", width=10, command=win.destroy).pack(side="left", padx=4)

        load_tk()

    def open_danhmuc_to():
        win = tk.Toplevel(root)
        win.title("Tổ chuyên môn")
        center_window(win, 540, 390)
        win.grab_set()
        win.focus_set()

        f_form = tk.LabelFrame(win, text=" Thông tin Tổ chuyên môn ", padx=10, pady=6)
        f_form.pack(fill="x", padx=12, pady=8)

        tk.Label(f_form, text="Mã Tổ:").grid(row=0, column=0, padx=5, pady=4, sticky="w")
        e_mato = tk.Entry(f_form, width=12)
        e_mato.grid(row=0, column=1, padx=5, pady=4, sticky="w")

        tk.Label(f_form, text="Tên Tổ:").grid(row=0, column=2, padx=10, pady=4, sticky="w")
        e_tento = tk.Entry(f_form, width=26)
        e_tento.grid(row=0, column=3, padx=5, pady=4, sticky="w")

        f_tree = tk.Frame(win)
        f_tree.pack(fill="both", expand=True, padx=12, pady=4)
        tree_pb = ttk.Treeview(f_tree, columns=("mato", "tento"), show="headings", height=8)
        tree_pb.heading("mato", text="Mã Tổ")
        tree_pb.heading("tento", text="Tên Tổ Chuyên Môn")
        tree_pb.column("mato", width=120, anchor="center")
        tree_pb.column("tento", width=360)
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
                cap_nhat_cbb_to_chinh()

        def xoa_pb():
            sel = tree_pb.selection()
            if not sel:
                return
            r = tree_pb.item(sel[0])["values"]
            conn = get_db_connection()
            if not conn:
                return
            cur = conn.cursor()
            try:
                cur.execute("SELECT COUNT(*) FROM HS_GiaoVien WHERE MaTo=%s", (r[0],))
                so_gv = cur.fetchone()[0]
                if so_gv > 0:
                    messagebox.showwarning(
                        "Không thể xóa",
                        f"Tổ '{r[1]}' đang có {so_gv} giáo viên trực thuộc!\n"
                        "Vui lòng chuyển giáo viên sang tổ khác trước khi xóa để không làm mất dữ liệu.",
                        parent=win
                    )
                    return
                if not messagebox.askyesno("Xác nhận", f"Xóa tổ '{r[1]}'?", parent=win):
                    return
                cur.execute("DELETE FROM DM_ToChuyenMon WHERE MaTo=%s", (r[0],))
                conn.commit()
                load_pb()
                cap_nhat_cbb_to_chinh()
            finally:
                cur.close()
                conn.close()

        tree_pb.bind("<<TreeviewSelect>>", chon_pb)

        f_btn = tk.Frame(win)
        f_btn.pack(pady=8)
        tk.Button(f_btn, text="Lưu", width=10, command=luu_pb).pack(side="left", padx=4)
        tk.Button(f_btn, text="Xóa", width=10, command=xoa_pb).pack(side="left", padx=4)
        tk.Button(f_btn, text="Đóng", width=10, command=win.destroy).pack(side="left", padx=4)

        load_pb()

    def open_danhmuc_chucvu():
        win = tk.Toplevel(root)
        win.title("Chức vụ & Mức giảm tiết")
        center_window(win, 600, 400)
        win.grab_set()
        win.focus_set()

        f_form = tk.LabelFrame(win, text=" Thông tin Chức vụ ", padx=10, pady=6)
        f_form.pack(fill="x", padx=12, pady=8)

        tk.Label(f_form, text="Mã CV:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        e_macv = tk.Entry(f_form, width=10)
        e_macv.grid(row=0, column=1, padx=4, pady=4, sticky="w")

        tk.Label(f_form, text="Tên CV:").grid(row=0, column=2, padx=6, pady=4, sticky="w")
        e_tencv = tk.Entry(f_form, width=22)
        e_tencv.grid(row=0, column=3, padx=4, pady=4, sticky="w")

        tk.Label(f_form, text="Tiết giảm:").grid(row=0, column=4, padx=6, pady=4, sticky="w")
        e_giam = tk.Entry(f_form, width=6)
        e_giam.insert(0, "0")
        e_giam.grid(row=0, column=5, padx=4, pady=4, sticky="w")

        f_tree = tk.Frame(win)
        f_tree.pack(fill="both", expand=True, padx=12, pady=4)
        tree_cv = ttk.Treeview(f_tree, columns=("macv", "tencv", "giam"), show="headings", height=8)
        tree_cv.heading("macv", text="Mã CV")
        tree_cv.heading("tencv", text="Tên Chức Vụ / Chế Độ")
        tree_cv.heading("giam", text="Tiết Giảm/Tuần")
        tree_cv.column("macv", width=100, anchor="center")
        tree_cv.column("tencv", width=310)
        tree_cv.column("giam", width=130, anchor="center")
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
            macv = e_macv.get().strip().upper()
            tencv = e_tencv.get().strip()
            try:
                giam = int(e_giam.get().strip())
            except ValueError:
                messagebox.showwarning("Lỗi", "Tiết giảm phải là số nguyên!", parent=win)
                return
            if not macv or not tencv:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập đủ thông tin!", parent=win)
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
                load_data_chinh()

        def xoa_cv():
            sel = tree_cv.selection()
            if not sel:
                return
            r = tree_cv.item(sel[0])["values"]
            conn = get_db_connection()
            if not conn:
                return
            cur = conn.cursor()
            try:
                cur.execute("SELECT COUNT(*) FROM QTr_KiemNhiem WHERE MaCV=%s", (r[0],))
                so_gv = cur.fetchone()[0]
                if so_gv > 0:
                    messagebox.showwarning(
                        "Không thể xóa",
                        f"Chức vụ '{r[1]}' đang có {so_gv} giáo viên đảm nhiệm!\n"
                        "Vui lòng gỡ phân công kiêm nhiệm trước khi xóa để không làm mất dữ liệu.",
                        parent=win
                    )
                    return
                if not messagebox.askyesno("Xác nhận", f"Xóa chức vụ '{r[1]}'?", parent=win):
                    return
                cur.execute("DELETE FROM DM_ChucVu WHERE MaCV=%s", (r[0],))
                conn.commit()
                load_cv()
                load_data_chinh()
            finally:
                cur.close()
                conn.close()

        tree_cv.bind("<<TreeviewSelect>>", chon_cv)

        f_btn = tk.Frame(win)
        f_btn.pack(pady=8)
        tk.Button(f_btn, text="Lưu", width=10, command=luu_cv).pack(side="left", padx=4)
        tk.Button(f_btn, text="Xóa", width=10, command=xoa_cv).pack(side="left", padx=4)
        tk.Button(f_btn, text="Đóng", width=10, command=win.destroy).pack(side="left", padx=4)

        load_cv()

    def open_kiemnhiem(magv_chon=None):
        win = tk.Toplevel(root)
        win.title("Phân công kiêm nhiệm")
        center_window(win, 660, 420)
        win.grab_set()
        win.focus_set()

        f_top = tk.LabelFrame(win, text=" Gán chức vụ kiêm nhiệm (Tối đa 02 chức vụ/GV) ", padx=10, pady=6)
        f_top.pack(fill="x", padx=12, pady=8)

        conn = get_db_connection()
        ds_gv = []
        ds_cv = []
        gv_gender = {}
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT MaGV, HoTen, GioiTinh FROM HS_GiaoVien ORDER BY MaGV")
            for mgv, ht, gt in cur.fetchall():
                ds_gv.append(f"{mgv} - {ht}")
                gv_gender[mgv] = gt
            cur.execute("SELECT MaCV, TenCV, SoTietGiam FROM DM_ChucVu WHERE SoTietGiam > 0 ORDER BY MaCV")
            for mcv, tcv, giam in cur.fetchall():
                ds_cv.append(f"{mcv} - {tcv} ({giam} tiết)")
            cur.close()
            conn.close()

        tk.Label(f_top, text="Giáo viên:").grid(row=0, column=0, padx=5, pady=4, sticky="w")
        cbb_gv = ttk.Combobox(f_top, values=ds_gv, width=28, state="readonly")
        if ds_gv:
            cbb_gv.current(0)
            if magv_chon:
                for item in ds_gv:
                    if item.startswith(f"{magv_chon} -"):
                        cbb_gv.set(item)
                        break
        cbb_gv.grid(row=0, column=1, padx=5, pady=4, sticky="w")

        tk.Label(f_top, text="Chức vụ:").grid(row=1, column=0, padx=5, pady=4, sticky="w")
        cbb_cv = ttk.Combobox(f_top, values=ds_cv, width=28, state="readonly")
        if ds_cv:
            cbb_cv.current(0)
        cbb_cv.grid(row=1, column=1, padx=5, pady=4, sticky="w")

        f_tree = tk.Frame(win)
        f_tree.pack(fill="both", expand=True, padx=12, pady=4)
        tree_kn = ttk.Treeview(f_tree, columns=("magv", "hoten", "macv", "tencv", "giam"), show="headings", height=8)
        tree_kn.heading("magv", text="Mã GV")
        tree_kn.heading("hoten", text="Họ và Tên")
        tree_kn.heading("macv", text="Mã CV")
        tree_kn.heading("tencv", text="Chức Vụ Kiêm Nhiệm")
        tree_kn.heading("giam", text="Tiết Giảm")
        tree_kn.column("magv", width=80, anchor="center")
        tree_kn.column("hoten", width=180)
        tree_kn.column("macv", width=70, anchor="center")
        tree_kn.column("tencv", width=200)
        tree_kn.column("giam", width=80, anchor="center")
        tree_kn.pack(fill="both", expand=True)

        def load_kn():
            for i in tree_kn.get_children():
                tree_kn.delete(i)
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT kn.MaGV, gv.HoTen, kn.MaCV, cv.TenCV, cv.SoTietGiam
                    FROM QTr_KiemNhiem kn
                    JOIN HS_GiaoVien gv ON kn.MaGV = gv.MaGV
                    JOIN DM_ChucVu cv ON kn.MaCV = cv.MaCV
                    ORDER BY kn.MaGV
                """)
                for r in cur.fetchall():
                    tree_kn.insert("", tk.END, values=r)
                cur.close()
                conn.close()

        def them_kn():
            if not cbb_gv.get() or not cbb_cv.get():
                return
            magv = cbb_gv.get().split(" - ")[0].strip()
            macv = cbb_cv.get().split(" - ")[0].strip()

            if macv == "CON" and gv_gender.get(magv) == "Nam":
                messagebox.showwarning("Không hợp lệ", "Chế độ con nhỏ < 12 tháng chỉ áp dụng cho giáo viên Nữ!", parent=win)
                return

            conn = get_db_connection()
            if not conn:
                return
            cur = conn.cursor()
            try:
                cur.execute("SELECT COUNT(*) FROM QTr_KiemNhiem WHERE MaGV=%s", (magv,))
                if cur.fetchone()[0] >= 2:
                    messagebox.showwarning("Giới hạn", f"Giáo viên {magv} đã đủ tối đa 02 chức vụ kiêm nhiệm!", parent=win)
                    return
                cur.execute("INSERT INTO QTr_KiemNhiem (MaGV, MaCV) VALUES (%s, %s)", (magv, macv))
                conn.commit()
                load_kn()
                load_data_chinh()
            except mysql.connector.IntegrityError:
                conn.rollback()
                messagebox.showwarning("Trùng", "Giáo viên đã được gán chức vụ này!", parent=win)
            finally:
                cur.close()
                conn.close()

        def xoa_kn():
            sel = tree_kn.selection()
            if not sel:
                messagebox.showwarning("Chú ý", "Chọn một dòng trong bảng bên dưới để xóa!", parent=win)
                return
            r = tree_kn.item(sel[0])["values"]
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM QTr_KiemNhiem WHERE MaGV=%s AND MaCV=%s", (r[0], r[2]))
                conn.commit()
                cur.close()
                conn.close()
                load_kn()
                load_data_chinh()

        f_btn = tk.Frame(f_top)
        f_btn.grid(row=0, column=2, rowspan=2, padx=12)
        tk.Button(f_btn, text="Thêm kiêm nhiệm", width=15, command=them_kn).pack(pady=2)
        tk.Button(f_btn, text="Xóa dòng chọn", width=15, command=xoa_kn).pack(pady=2)

        tk.Button(win, text="Đóng", width=10, command=win.destroy).pack(pady=6)
        load_kn()

    # GIAO DIỆN MÀN HÌNH CHÍNH
    tk.Label(root, text="QUẢN LÝ HỒ SƠ GIÁO VIÊN", font=("Arial", 15, "bold"), fg="#0d47a1").pack(pady=(10, 4))

    # Khu vực 1: Nhập thông tin hồ sơ giáo viên
    frame_info = tk.LabelFrame(root, text=" Thông tin giáo viên ", font=("Arial", 9, "bold"), padx=12, pady=8)
    frame_info.pack(fill="x", padx=12, pady=4)

    tk.Label(frame_info, text="Mã GV:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    entry_magv = tk.Entry(frame_info, width=16)
    entry_magv.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    tk.Label(frame_info, text="Họ và tên:").grid(row=0, column=2, padx=12, pady=5, sticky="w")
    entry_hoten = tk.Entry(frame_info, width=28)
    entry_hoten.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    tk.Label(frame_info, text="Giới tính:").grid(row=0, column=4, padx=12, pady=5, sticky="w")
    gender_var = tk.StringVar(value="Nam")
    f_gender = tk.Frame(frame_info)
    f_gender.grid(row=0, column=5, padx=5, pady=5, sticky="w")
    tk.Radiobutton(f_gender, text="Nam", variable=gender_var, value="Nam").pack(side="left")
    tk.Radiobutton(f_gender, text="Nữ", variable=gender_var, value="Nữ").pack(side="left", padx=10)

    tk.Label(frame_info, text="Ngày sinh:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    if HAS_TKCALENDAR:
        date_entry = DateEntry(frame_info, width=14, background="darkblue",
                               foreground="white", date_pattern="dd/MM/yyyy")
        date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    else:
        date_entry = tk.Entry(frame_info, width=16)
        date_entry.insert(0, "01/01/1990")
        date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    tk.Label(frame_info, text="Tổ bộ môn:").grid(row=1, column=2, padx=12, pady=5, sticky="w")
    f_to = tk.Frame(frame_info)
    f_to.grid(row=1, column=3, padx=5, pady=5, sticky="w")
    cbb_to = ttk.Combobox(f_to, values=ds_ten_to, width=22)
    if ds_ten_to:
        cbb_to.current(0)
    cbb_to.pack(side="left")

    tk.Label(frame_info, text="Trình độ:").grid(row=1, column=4, padx=12, pady=5, sticky="w")
    ds_trinhdo = ["Cử nhân Sư phạm", "Thạc sĩ", "Tiến sĩ", "Cao đẳng Sư phạm"]
    f_td = tk.Frame(frame_info)
    f_td.grid(row=1, column=5, padx=5, pady=5, sticky="w")
    cbb_trinhdo = ttk.Combobox(f_td, values=ds_trinhdo, width=15)
    cbb_trinhdo.current(0)
    cbb_trinhdo.pack(side="left")

    # Khu vực 2: Tìm kiếm, Lọc theo Tổ & Chọn Cấp trường
    frame_filter = tk.Frame(root, pady=4)
    frame_filter.pack(fill="x", padx=12)

    tk.Label(frame_filter, text="Tìm kiếm:").pack(side="left", padx=(0, 4))
    entry_timkiem = tk.Entry(frame_filter, width=22)
    entry_timkiem.pack(side="left", padx=4)

    tk.Label(frame_filter, text="Lọc theo Tổ:").pack(side="left", padx=(12, 4))
    cbb_loc_to = ttk.Combobox(frame_filter, values=["Tất cả"] + ds_ten_to, width=18, state="readonly")
    cbb_loc_to.current(0)
    cbb_loc_to.pack(side="left", padx=4)

    tk.Label(frame_filter, text="Cấp trường:").pack(side="left", padx=(16, 4))
    cbb_loaitruong = ttk.Combobox(frame_filter, values=list(LOAI_TRUONG_MAP.keys()), width=16, state="readonly")
    cbb_loaitruong.current(0)
    cbb_loaitruong.pack(side="left", padx=4)

    # Khu vực 3: Bảng hiển thị Treeview
    frame_tree = tk.Frame(root)
    frame_tree.pack(fill="both", expand=True, padx=12, pady=4)

    cols = ("magv", "hoten", "phai", "ngaysinh", "to", "trinhdo", "chucvu", "giam", "day")
    tree = ttk.Treeview(frame_tree, columns=cols, show="headings", height=12)
    tree.heading("magv",     text="Mã GV")
    tree.heading("hoten",    text="Họ và Tên")
    tree.heading("phai",     text="Phái")
    tree.heading("ngaysinh", text="Ngày Sinh")
    tree.heading("to",       text="Tổ Chuyên Môn")
    tree.heading("trinhdo",  text="Trình Độ")
    tree.heading("chucvu",   text="Kiêm Nhiệm")
    tree.heading("giam",     text="Giảm Trừ")
    tree.heading("day",      text="Định Mức Tiết")

    tree.column("magv",     width=65,  anchor="center")
    tree.column("hoten",    width=160)
    tree.column("phai",     width=50,  anchor="center")
    tree.column("ngaysinh", width=85,  anchor="center")
    tree.column("to",       width=120)
    tree.column("trinhdo",  width=115)
    tree.column("chucvu",   width=175)
    tree.column("giam",     width=75,  anchor="center")
    tree.column("day",      width=90,  anchor="center")

    sb = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    def cap_nhat_cbb_to_chinh():
        global to_map, rev_to_map, ds_ten_to
        to_map = lay_ds_to()
        rev_to_map = {v: k for k, v in to_map.items()}
        ds_ten_to = list(to_map.values())
        cbb_to["values"] = ds_ten_to
        cbb_loc_to["values"] = ["Tất cả"] + ds_ten_to
        load_data_chinh()

    def them_nhanh_to():
        """Thêm nhanh giá trị mới cho Combobox Tổ bộ môn và lưu vào CSDL."""
        win_to = tk.Toplevel(root)
        win_to.title("Thêm tổ bộ môn")
        center_window(win_to, 340, 165)
        win_to.grab_set()
        win_to.focus_set()

        f = tk.Frame(win_to, padx=14, pady=12)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Mã Tổ (VD: TD):").grid(row=0, column=0, pady=5, sticky="w")
        e_ma = tk.Entry(f, width=18)
        e_ma.grid(row=0, column=1, pady=5, padx=6)

        tk.Label(f, text="Tên Tổ bộ môn:").grid(row=1, column=0, pady=5, sticky="w")
        e_ten = tk.Entry(f, width=18)
        dang_nhap = cbb_to.get().strip()
        if dang_nhap and dang_nhap not in ds_ten_to:
            e_ten.insert(0, dang_nhap)
        e_ten.grid(row=1, column=1, pady=5, padx=6)

        def luu_to_moi():
            mato = e_ma.get().strip().upper()
            tento = e_ten.get().strip()
            if not mato or not tento:
                messagebox.showwarning("Chú ý", "Vui lòng nhập đầy đủ Mã Tổ và Tên Tổ!", parent=win_to)
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
                cap_nhat_cbb_to_chinh()
                cbb_to.set(tento)
                win_to.destroy()

        f_b = tk.Frame(f)
        f_b.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(f_b, text="Thêm", width=9, command=luu_to_moi).pack(side="left", padx=4)
        tk.Button(f_b, text="Hủy", width=9, command=win_to.destroy).pack(side="left", padx=4)

    def them_nhanh_trinhdo():
        """Thêm nhanh giá trị mới cho Combobox Trình độ."""
        win_td = tk.Toplevel(root)
        win_td.title("Thêm trình độ")
        center_window(win_td, 330, 130)
        win_td.grab_set()
        win_td.focus_set()

        f = tk.Frame(win_td, padx=14, pady=12)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Tên Trình độ:").grid(row=0, column=0, pady=6, sticky="w")
        e_td = tk.Entry(f, width=18)
        dang_nhap = cbb_trinhdo.get().strip()
        if dang_nhap and dang_nhap not in ds_trinhdo:
            e_td.insert(0, dang_nhap)
        e_td.grid(row=0, column=1, pady=6, padx=6)

        def luu_td_moi():
            td_moi = e_td.get().strip()
            if not td_moi:
                messagebox.showwarning("Chú ý", "Vui lòng nhập tên Trình độ!", parent=win_td)
                return
            if td_moi not in ds_trinhdo:
                ds_trinhdo.append(td_moi)
                cbb_trinhdo["values"] = ds_trinhdo
            cbb_trinhdo.set(td_moi)
            win_td.destroy()

        f_b = tk.Frame(f)
        f_b.grid(row=1, column=0, columnspan=2, pady=8)
        tk.Button(f_b, text="Thêm", width=9, command=luu_td_moi).pack(side="left", padx=4)
        tk.Button(f_b, text="Hủy", width=9, command=win_td.destroy).pack(side="left", padx=4)

    btn_them_to = tk.Button(f_to, text="+", width=2, command=them_nhanh_to)
    btn_them_to.pack(side="left", padx=(3, 0))

    btn_them_td = tk.Button(f_td, text="+", width=2, command=them_nhanh_trinhdo)
    btn_them_td.pack(side="left", padx=(3, 0))

    def lay_hoac_them_mato(ten_to_nhap):
        """Lấy Mã Tổ từ Combobox; nếu người dùng gõ Tổ mới chưa có thì tự động thêm vào CSDL."""
        ten_to_nhap = ten_to_nhap.strip()
        if not ten_to_nhap:
            return "TOAN"
        if ten_to_nhap in rev_to_map:
            return rev_to_map[ten_to_nhap]
        chu_cai = "".join([tu[0].upper() for tu in ten_to_nhap.split() if tu])
        mato_moi = (chu_cai if chu_cai else "TO")[:6]
        idx = 1
        goc = mato_moi
        while mato_moi in to_map:
            mato_moi = f"{goc}{idx}"
            idx += 1
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO DM_ToChuyenMon (MaTo, TenTo) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE TenTo=VALUES(TenTo)",
                (mato_moi, ten_to_nhap)
            )
            conn.commit()
            cur.close()
            conn.close()
            cap_nhat_cbb_to_chinh()
            cbb_to.set(ten_to_nhap)
        return mato_moi

    def load_data_chinh():
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

        for magv, hoten, phai, ngaysinh, mato, trinhdo in rows:
            tento = to_map.get(mato, mato)
            td = trinhdo if trinhdo else "Cử nhân Sư phạm"
            if td not in ds_trinhdo:
                ds_trinhdo.append(td)
                cbb_trinhdo["values"] = ds_trinhdo
            if tu_khoa and (tu_khoa not in magv.lower() and tu_khoa not in hoten.lower()):
                continue
            if ten_to_loc != "Tất cả" and tento != ten_to_loc:
                continue

            cv_str, giam, day = lay_thong_tin_kiem_nhiem(conn, magv)
            tree.insert("", tk.END, values=(
                magv, hoten, phai, format_date_vn(ngaysinh),
                tento, td, cv_str, f"{giam} tiết", f"{day} tiết"
            ))
        conn.close()

    def doi_cap_truong(event=None):
        global CURRENT_DINH_MUC
        CURRENT_DINH_MUC = LOAI_TRUONG_MAP.get(cbb_loaitruong.get(), 17)
        load_data_chinh()

    tk.Button(frame_filter, text="Tìm", width=8, command=load_data_chinh).pack(side="left", padx=4)
    cbb_loc_to.bind("<<ComboboxSelected>>", lambda e: load_data_chinh())
    cbb_loaitruong.bind("<<ComboboxSelected>>", doi_cap_truong)

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
        tree.selection_remove(tree.selection())

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
        magv     = entry_magv.get().strip().upper()
        hoten    = entry_hoten.get().strip()
        phai     = gender_var.get()
        ngaysinh = _get_ngaysinh_mysql()
        trinhdo  = cbb_trinhdo.get().strip()

        if not magv or not hoten:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Mã GV và Họ tên!")
            return

        tien_to, phan_so = tach_tien_to_va_so(magv)
        if tien_to != MA_TIEN_TO or not phan_so.isdigit():
            messagebox.showwarning(
                "Mã không đồng nhất",
                f"Toàn bộ mã phải mở đầu bằng tiền tố cố định '{MA_TIEN_TO}' kèm chữ số (VD: {MA_TIEN_TO}001)!"
            )
            return

        mato = lay_hoac_them_mato(cbb_to.get())
        if trinhdo and trinhdo not in ds_trinhdo:
            ds_trinhdo.append(trinhdo)
            cbb_trinhdo["values"] = ds_trinhdo

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
            load_data_chinh()
            clear_form()
            messagebox.showinfo("Thành công", f"Đã thêm giáo viên {hoten} ({magv})")
        except mysql.connector.IntegrityError:
            conn.rollback()
            messagebox.showwarning("Trùng mã", f"Mã '{magv}' đã tồn tại!")
        finally:
            cur.close()
            conn.close()

    def sua_gv():
        global MA_TIEN_TO
        sel = tree.selection()
        new_magv = entry_magv.get().strip().upper()
        if not new_magv:
            messagebox.showwarning("Cảnh báo", "Chọn một giáo viên trên bảng để sửa!")
            return

        tien_to_moi, phan_so_moi = tach_tien_to_va_so(new_magv)
        if not tien_to_moi or not tien_to_moi.isalpha() or not phan_so_moi.isdigit():
            messagebox.showwarning(
                "Sai quy tắc mã",
                f"Mã phải mở đầu bằng chữ cái hợp lệ kèm chữ số (VD: {MA_TIEN_TO}001, NV001)!"
            )
            return

        old_magv = str(tree.item(sel[0])["values"][0]).strip() if sel else new_magv
        hoten    = entry_hoten.get().strip()
        phai     = gender_var.get()
        ngaysinh = _get_ngaysinh_mysql()
        mato     = lay_hoac_them_mato(cbb_to.get())
        trinhdo  = cbb_trinhdo.get().strip()
        if trinhdo and trinhdo not in ds_trinhdo:
            ds_trinhdo.append(trinhdo)
            cbb_trinhdo["values"] = ds_trinhdo

        doi_toan_bo_tien_to = False
        if tien_to_moi != MA_TIEN_TO:
            if not messagebox.askyesno(
                "Đồng bộ tiền tố mã",
                f"Bạn vừa đổi tiền tố mã từ '{MA_TIEN_TO}' sang '{tien_to_moi}'.\n"
                f"Để toàn bộ mã mở đầu đều giống nhau, hệ thống sẽ đổi đồng loạt tất cả mã sang '{tien_to_moi}'.\n"
                "Bạn có đồng ý không?"
            ):
                return
            doi_toan_bo_tien_to = True

        conn = get_db_connection()
        if conn is None:
            return
        cur = conn.cursor()
        try:
            _, so_cu = tach_tien_to_va_so(old_magv)
            if phan_so_moi != so_cu:
                ma_kiem_tra = MA_TIEN_TO + phan_so_moi
                cur.execute("SELECT MaGV FROM HS_GiaoVien WHERE MaGV=%s", (ma_kiem_tra,))
                if cur.fetchone():
                    messagebox.showwarning("Trùng mã", f"Số thứ tự mã '{phan_so_moi}' đã tồn tại!")
                    return

            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            if doi_toan_bo_tien_to:
                cur.execute("SELECT MaGV FROM HS_GiaoVien")
                ds_tat_ca = [r[0] for r in cur.fetchall()]
                for ma_hien_tai in ds_tat_ca:
                    _, duoi_so = tach_tien_to_va_so(str(ma_hien_tai))
                    if ma_hien_tai == old_magv:
                        duoi_so = phan_so_moi
                    ma_cap_nhat = tien_to_moi + duoi_so
                    cur.execute("UPDATE HS_GiaoVien SET MaGV=%s WHERE MaGV=%s", (ma_cap_nhat, ma_hien_tai))
                    cur.execute("UPDATE QTr_KiemNhiem SET MaGV=%s WHERE MaGV=%s", (ma_cap_nhat, ma_hien_tai))
                MA_TIEN_TO = tien_to_moi
                new_magv = tien_to_moi + phan_so_moi
            elif new_magv != old_magv:
                cur.execute("UPDATE HS_GiaoVien SET MaGV=%s WHERE MaGV=%s", (new_magv, old_magv))
                cur.execute("UPDATE QTr_KiemNhiem SET MaGV=%s WHERE MaGV=%s", (new_magv, old_magv))

            cur.execute(
                "UPDATE HS_GiaoVien SET HoTen=%s, GioiTinh=%s, NgaySinh=%s, MaTo=%s, TrinhDo=%s WHERE MaGV=%s",
                (hoten, phai, ngaysinh, mato, trinhdo, new_magv)
            )
            cur.execute("SET FOREIGN_KEY_CHECKS=1")
            conn.commit()
            load_data_chinh()
            clear_form()
            if doi_toan_bo_tien_to:
                messagebox.showinfo("Thành công", f"Đã đổi đồng nhất toàn bộ mã sang tiền tố '{MA_TIEN_TO}' và lưu thông tin!")
            else:
                messagebox.showinfo("Thành công", f"Đã cập nhật thông tin ({new_magv})!")
        finally:
            cur.close()
            conn.close()

    def open_doi_tien_to():
        """Cửa sổ cho phép Admin đổi tiền tố chữ cái mở đầu đồng nhất cho toàn bộ danh sách."""
        win_db = tk.Toplevel(root)
        win_db.title("Đổi tiền tố mã")
        center_window(win_db, 350, 165)
        win_db.grab_set()
        win_db.focus_set()

        f = tk.Frame(win_db, padx=16, pady=12)
        f.pack(fill="both", expand=True)

        tk.Label(f, text=f"Tiền tố cố định hiện tại: {MA_TIEN_TO}", font=("Arial", 9, "bold"), fg="#0d47a1").grid(
            row=0, column=0, columnspan=2, pady=(0, 8), sticky="w"
        )
        tk.Label(f, text="Tiền tố mới (chữ cái):").grid(row=1, column=0, pady=6, sticky="w")
        e_tt = tk.Entry(f, width=16)
        e_tt.insert(0, "NV" if MA_TIEN_TO == "GV" else "GV")
        e_tt.grid(row=1, column=1, pady=6, padx=6, sticky="w")

        def thuc_hien_doi():
            global MA_TIEN_TO
            dich = e_tt.get().strip().upper()
            if not dich or not dich.isalpha():
                messagebox.showwarning(
                    "Không hợp lệ",
                    "Tiền tố mã bắt buộc phải là các chữ cái (VD: GV, NV, CB)!",
                    parent=win_db
                )
                return
            if dich == MA_TIEN_TO:
                messagebox.showinfo("Thông báo", f"Toàn bộ mã hiện đã dùng tiền tố '{dich}'!", parent=win_db)
                return
            conn = get_db_connection()
            if not conn:
                return
            cur = conn.cursor()
            try:
                cur.execute("SELECT MaGV FROM HS_GiaoVien")
                ds_ma = [r[0] for r in cur.fetchall()]
                cur.execute("SET FOREIGN_KEY_CHECKS=0")
                for ma_cu in ds_ma:
                    _, duoi_so = tach_tien_to_va_so(str(ma_cu))
                    ma_moi = dich + duoi_so
                    cur.execute("UPDATE HS_GiaoVien SET MaGV=%s WHERE MaGV=%s", (ma_moi, ma_cu))
                    cur.execute("UPDATE QTr_KiemNhiem SET MaGV=%s WHERE MaGV=%s", (ma_moi, ma_cu))
                cur.execute("SET FOREIGN_KEY_CHECKS=1")
                conn.commit()
                MA_TIEN_TO = dich
                load_data_chinh()
                clear_form()
                win_db.destroy()
                messagebox.showinfo("Thành công", f"Đã đổi toàn bộ mã mở đầu sang '{MA_TIEN_TO}'!")
            finally:
                cur.close()
                conn.close()

        f_b = tk.Frame(f)
        f_b.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(f_b, text="Lưu", width=10, command=thuc_hien_doi).pack(side="left", padx=5)
        tk.Button(f_b, text="Đóng", width=10, command=win_db.destroy).pack(side="left", padx=5)

    def xoa_gv():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Cảnh báo", "Chọn giáo viên cần xóa!")
            return
        r = tree.item(sel[0])["values"]
        if not messagebox.askyesno("Xác nhận", f"Xóa giáo viên {r[1]} ({r[0]})?"):
            return
        conn = get_db_connection()
        if conn is None:
            return
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM HS_GiaoVien WHERE MaGV=%s", (r[0],))
            conn.commit()
            load_data_chinh()
            clear_form()
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

        entry_hoten.delete(0, tk.END)
        entry_hoten.insert(0, r[1])
        gender_var.set(r[2])

        if HAS_TKCALENDAR:
            try:
                parts = str(r[3]).split("/")
                if len(parts) == 3:
                    date_entry.set_date(date(int(parts[2]), int(parts[1]), int(parts[0])))
            except Exception:
                pass
        else:
            date_entry.delete(0, tk.END)
            date_entry.insert(0, str(r[3]))

        cbb_to.set(r[4])
        cbb_trinhdo.set(r[5])

    tree.bind("<<TreeviewSelect>>", chon_dong)

    # Khu vực 4: Các nút điều khiển
    f_btn = tk.Frame(root)
    f_btn.pack(pady=10)

    btn_them = tk.Button(f_btn, text="Thêm",      width=10, command=them_gv)
    btn_sua  = tk.Button(f_btn, text="Sửa / Lưu", width=10, command=sua_gv)
    btn_xoa  = tk.Button(f_btn, text="Xóa",       width=10, command=xoa_gv)
    btn_moi  = tk.Button(f_btn, text="Làm mới",   width=10, command=clear_form)
    btn_kn   = tk.Button(
        f_btn, text="Kiêm nhiệm", width=12, bg="#0d47a1", fg="white",
        font=("Arial", 9, "bold"), command=lambda: open_kiemnhiem(entry_magv.get().strip())
    )
    btn_xuat = tk.Button(
        f_btn, text="Xuất Excel", width=12, bg="#27ae60", fg="white",
        font=("Arial", 9, "bold"), command=lambda: xuat_excel(root)
    )

    btn_them.grid(row=0, column=0, padx=5)
    btn_sua.grid(row=0,  column=1, padx=5)
    btn_xoa.grid(row=0,  column=2, padx=5)
    btn_moi.grid(row=0,  column=3, padx=5)
    btn_kn.grid(row=0,   column=4, padx=5)
    btn_xuat.grid(row=0, column=5, padx=5)

    # THANH MENU
    def dang_xuat():
        root.destroy()
        mo_cua_so_dang_nhap()

    menubar = tk.Menu(root)

    menu_hethong = tk.Menu(menubar, tearoff=0)
    menu_hethong.add_command(label="Làm mới dữ liệu",   command=load_data_chinh)
    menu_hethong.add_command(label="Xuất Excel",        command=lambda: xuat_excel(root))
    menu_hethong.add_separator()
    menu_hethong.add_command(label="Đổi mật khẩu",      command=open_doi_mat_khau)
    menu_hethong.add_command(label="Quản lý tài khoản", command=open_quanly_taikhoan)
    menu_hethong.add_separator()
    menu_hethong.add_command(label="Đăng xuất",         command=dang_xuat)
    menu_hethong.add_command(label="Thoát",             command=root.destroy)
    menubar.add_cascade(label="Hệ thống", menu=menu_hethong)

    menu_danhmuc = tk.Menu(menubar, tearoff=0)
    menu_danhmuc.add_command(label="Tổ chuyên môn", command=open_danhmuc_to)
    menu_danhmuc.add_command(label="Chức vụ",       command=open_danhmuc_chucvu)
    menubar.add_cascade(label="Danh mục", menu=menu_danhmuc)

    menu_nghiepvu = tk.Menu(menubar, tearoff=0)
    menu_nghiepvu.add_command(label="Phân công kiêm nhiệm", command=open_kiemnhiem)
    menu_nghiepvu.add_command(label="Đổi tiền tố mã",       command=open_doi_tien_to)
    menubar.add_cascade(label="Nghiệp vụ", menu=menu_nghiepvu)

    menu_trogiup = tk.Menu(menubar, tearoff=0)
    menu_trogiup.add_command(
        label="Thông tin",
        command=lambda: messagebox.showinfo(
            "Thông tin",
            "Phần mềm Quản lý Giáo viên Phổ thông\n\n"
            "Thực hiện:\n"
            "- Nguyễn Huỳnh Nhựt Tân (DTH245880)\n"
            "- Nguyễn Trọng Tín (DTH245912)",
            parent=root
        )
    )
    menu_trogiup.add_command(
        label="Hướng dẫn sử dụng",
        command=lambda: messagebox.showinfo(
            "Hướng dẫn",
            "1. Nhập thông tin giáo viên vào các ô trên cùng.\n"
            "2. Nhấn 'Thêm' để thêm giáo viên mới.\n"
            "3. Chọn giáo viên từ bảng để sửa hoặc xóa.\n"
            "4. Nhấn nút '+' cạnh Combobox để thêm tổ bộ môn / trình độ.\n"
            "5. Vào Hệ thống -> Đổi mật khẩu để thay đổi mật khẩu cá nhân.",
            parent=root
        )
    )
    menubar.add_cascade(label="Trợ giúp", menu=menu_trogiup)

    root.config(menu=menubar)

    # GIAI ĐOẠN 4: PHÂN QUYỀN GIAO DIỆN (ROLE-BASED UI)
    if role != "admin":
        btn_them.config(state="disabled")
        btn_sua.config(state="disabled")
        btn_xoa.config(state="disabled")
        btn_kn.config(state="disabled", bg="#9e9e9e")
        btn_them_to.config(state="disabled")
        btn_them_td.config(state="disabled")
        menu_hethong.entryconfig("Quản lý tài khoản", state="disabled")
        menubar.entryconfig("Danh mục", state="disabled")
        menubar.entryconfig("Nghiệp vụ", state="disabled")

    load_data_chinh()
    root.mainloop()


# 4. GIAI ĐOẠN 1, 2 , 3: CỬA SỔ ĐĂNG NHẬP, XÁC THỰC NGƯỜI DÙNG
def mo_cua_so_dang_nhap():
    login_win = tk.Tk()
    login_win.title("Đăng nhập hệ thống")
    center_window(login_win, 370, 210)
    login_win.resizable(False, False)

    tk.Label(login_win, text="ĐĂNG NHẬP HỆ THỐNG", font=("Arial", 13, "bold"), fg="#0d47a1").pack(pady=(16, 10))

    f_input = tk.Frame(login_win, padx=20)
    f_input.pack(fill="x")

    tk.Label(f_input, text="Tài khoản:", width=11, anchor="w").grid(row=0, column=0, pady=6)
    e_user = tk.Entry(f_input, width=25)
    e_user.insert(0, "admin")
    e_user.grid(row=0, column=1, pady=6)

    tk.Label(f_input, text="Mật khẩu:", width=11, anchor="w").grid(row=1, column=0, pady=6)
    e_pass = tk.Entry(f_input, width=25, show="*")
    e_pass.insert(0, "123456")
    e_pass.grid(row=1, column=1, pady=6)

    def xu_ly_dang_nhap(event=None):
        username = e_user.get().strip()
        password = e_pass.get().strip()
        if not username or not password:
            messagebox.showwarning("Chú ý", "Vui lòng nhập đầy đủ tài khoản và mật khẩu!", parent=login_win)
            return

        conn = get_db_connection()
        if conn is None:
            return
        cur = conn.cursor()
        try:
            # Giai đoạn 2: Truy vấn tài khoản và đối chiếu mật khẩu Hash SHA-256
            cur.execute("SELECT MatKhau, Quyen FROM TaiKhoan WHERE TenDangNhap = %s", (username,))
            row = cur.fetchone()
        finally:
            cur.close()
            conn.close()

        # Giai đoạn 3: Xử lý kết quả đăng nhập
        if row and row[0] == ma_hoa_mk(password):
            role = row[1]
            login_win.destroy()
            mo_man_hinh_chinh(role=role, username=username)
        else:
            messagebox.showerror("Lỗi đăng nhập", "Sai tài khoản hoặc mật khẩu!", parent=login_win)

    e_pass.bind("<Return>", xu_ly_dang_nhap)

    f_btn = tk.Frame(login_win)
    f_btn.pack(pady=12)
    tk.Button(
        f_btn, text="Đăng nhập", width=12, bg="#0d47a1", fg="white",
        font=("Arial", 9, "bold"), command=xu_ly_dang_nhap
    ).pack(side="left", padx=6)
    tk.Button(f_btn, text="Thoát", width=10, command=login_win.destroy).pack(side="left", padx=6)

    login_win.mainloop()


if __name__ == "__main__":
    init_db()
    mo_cua_so_dang_nhap()
