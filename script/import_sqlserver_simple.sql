



USE BANHANG;
GO


PRINT '=== BƯỚC 1: Kiểm tra FK constraints ===';
GO

SELECT CONSTRAINT_NAME, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE CONSTRAINT_TYPE = 'FOREIGN KEY'
ORDER BY TABLE_NAME;

GO


PRINT '';
PRINT '=== BƯỚC 2: Xóa dữ liệu cũ ===';
GO

USE BANHANG;
GO

-- Xóa theo thứ tự FK (child → parent)
-- Không cần NOCHECK vì DELETE không bị FK constraint

DELETE FROM dbo.MatHang_DuocDat;
PRINT 'Đã xóa MatHang_DuocDat: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' rows';

DELETE FROM dbo.DonDatHang;
PRINT 'Đã xóa DonDatHang: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' rows';

DELETE FROM dbo.MatHang_LuuTru;
PRINT 'Đã xóa MatHang_LuuTru: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' rows';

DELETE FROM dbo.CuaHang;
PRINT 'Đã xóa CuaHang: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' rows';

DELETE FROM dbo.MatHang;
PRINT 'Đã xóa MatHang: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' rows';

DELETE FROM dbo.VanPhongDaiDien;
PRINT 'Đã xóa VanPhongDaiDien: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' rows';

GO

PRINT '';
PRINT 'Dữ liệu cũ đã được xóa. Sẵn sàng import.';
GO



USE BANHANG;
GO

SELECT 'VanPhongDaiDien' AS [Table], COUNT(*) AS [Rows] FROM dbo.VanPhongDaiDien
UNION ALL
SELECT 'MatHang', COUNT(*) FROM dbo.MatHang
UNION ALL
SELECT 'CuaHang', COUNT(*) FROM dbo.CuaHang
UNION ALL
SELECT 'MatHang_LuuTru', COUNT(*) FROM dbo.MatHang_LuuTru
UNION ALL
SELECT 'DonDatHang', COUNT(*) FROM dbo.DonDatHang
UNION ALL
SELECT 'MatHang_DuocDat', COUNT(*) FROM dbo.MatHang_DuocDat;

GO



select count(*) from VanPhongDaiDien;

-- lưu ý:Bật SQLCMD Mode trong SSMS trước - tránh lỗi Incorrect syntax near ':'.
:r "D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output\01_van_phong_dai_dien.sql"
:r "D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output\02_mat_hang.sql"
:r "D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output\03_cua_hang.sql"
:r "D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output\07_mat_hang_duoc_luu_tru.sql"
:r "D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output\08_don_dat_hang.sql"
:r "D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output\09_mat_hang_duoc_dat.sql"


-- @D:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\output\06_khach_hang_buu_dien.sql



USE BANHANG;
GO

-- Kiểm tra cột trong DonDatHang
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'DonDatHang';

-- Kiểm tra cột trong DonDatHang
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 

WHERE TABLE_NAME = 'mathang_duocdat';

-- Kiểm tra tên bảng
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'dbo';