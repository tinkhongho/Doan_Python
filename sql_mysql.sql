-- ==============================================================
-- ĐỒ ÁN CHUYÊN ĐỀ PYTHON (COS525) - TRƯỜNG ĐẠI HỌC AN GIANG
-- Đề tài: Xây dựng ứng dụng Quản lý Giáo viên THPT
-- Nhóm 14 - Tổ 1 - Lớp DH25TH3
-- Sinh viên: Nguyễn Huỳnh Nhựt Tân (DTH245880) & Nguyễn Trọng Tín (DTH245912)
-- GVHD: ThS. Nguyễn Ngọc Minh
-- Hệ quản trị CSDL: MySQL Server 8.0 / MySQL Workbench
-- ==============================================================

CREATE DATABASE IF NOT EXISTS qlgiaovien
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE qlgiaovien;

-- 1. Bảng Danh mục Tổ chuyên môn
CREATE TABLE IF NOT EXISTS DM_ToChuyenMon (
    MaTo VARCHAR(10) PRIMARY KEY,
    TenTo VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Bảng Danh mục Chức vụ & Chế độ giảm trừ (Lưu quy định số tiết giảm)
CREATE TABLE IF NOT EXISTS DM_ChucVu (
    MaCV VARCHAR(10) PRIMARY KEY,
    TenCV VARCHAR(100) NOT NULL,
    SoTietGiam INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Bảng Hồ sơ Giáo viên
CREATE TABLE IF NOT EXISTS HS_GiaoVien (
    MaGV VARCHAR(20) PRIMARY KEY,
    HoTen VARCHAR(100) NOT NULL,
    GioiTinh VARCHAR(10),
    NgaySinh DATE,
    MaTo VARCHAR(10),
    TrinhDo VARCHAR(50),
    FOREIGN KEY (MaTo) REFERENCES DM_ToChuyenMon(MaTo) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Bảng Quá trình Kiêm nhiệm (Giải quyết quan hệ Nhiều - Nhiều N-N)
CREATE TABLE IF NOT EXISTS QTr_KiemNhiem (
    MaGV VARCHAR(20),
    MaCV VARCHAR(10),
    PRIMARY KEY (MaGV, MaCV),
    FOREIGN KEY (MaGV) REFERENCES HS_GiaoVien(MaGV) ON DELETE CASCADE,
    FOREIGN KEY (MaCV) REFERENCES DM_ChucVu(MaCV) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==============================================================
-- NẠP DỮ LIỆU DANH MỤC BAN ĐẦU (MASTER DATA)
-- ==============================================================

INSERT INTO DM_ToChuyenMon (MaTo, TenTo) VALUES
('TOAN', 'Toán - Tin'),
('VAN',  'Ngữ Văn'),
('ANH',  'Ngoại Ngữ'),
('KHTN', 'Lý - Hóa - Sinh'),
('KHXH', 'Sử - Địa - GDCD'),
('VP',   'Tổ Văn phòng')
ON DUPLICATE KEY UPDATE TenTo=VALUES(TenTo);

INSERT INTO DM_ChucVu (MaCV, TenCV, SoTietGiam) VALUES
('GV',  'Giáo viên bộ môn',                0),
('CN',  'Chủ nhiệm lớp',                   4),
('TT',  'Tổ trưởng chuyên môn',            3),
('TP',  'Tổ phó chuyên môn',               1),
('CD',  'Bí thư Đoàn',                     3),
('CON', 'Giáo viên nữ có con < 12 tháng',  3)
ON DUPLICATE KEY UPDATE TenCV=VALUES(TenCV), SoTietGiam=VALUES(SoTietGiam);

INSERT INTO HS_GiaoVien (MaGV, HoTen, GioiTinh, NgaySinh, MaTo, TrinhDo) VALUES
('GV001', 'Nguyễn Văn An',      'Nam', '1985-04-12', 'TOAN', 'Thạc sĩ'),
('GV002', 'Trần Thị Bích Ngọc', 'Nữ',  '1992-11-20', 'VAN',  'Cử nhân Sư phạm'),
('GV003', 'Lê Hoàng Minh',      'Nam', '1998-08-15', 'ANH',  'Cử nhân Sư phạm'),
('GV004', 'Phạm Hồng Loan',     'Nữ',  '1988-01-30', 'KHTN', 'Thạc sĩ'),
('GV005', 'Nguyễn Thị Lan',     'Nữ',  '1994-06-25', 'KHXH', 'Cử nhân Sư phạm')
ON DUPLICATE KEY UPDATE
    HoTen=VALUES(HoTen),
    GioiTinh=VALUES(GioiTinh),
    NgaySinh=VALUES(NgaySinh),
    MaTo=VALUES(MaTo),
    TrinhDo=VALUES(TrinhDo);

INSERT INTO QTr_KiemNhiem (MaGV, MaCV) VALUES
('GV001', 'TT'),
('GV002', 'CN'),
('GV002', 'CON'),
('GV003', 'CD'),
('GV005', 'CN')
ON DUPLICATE KEY UPDATE MaCV=VALUES(MaCV);
