-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: qlgiaovien
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `dm_chucvu`
--

LOCK TABLES `dm_chucvu` WRITE;
/*!40000 ALTER TABLE `dm_chucvu` DISABLE KEYS */;
INSERT INTO `dm_chucvu` VALUES ('CD','Bí thư Đoàn',3),('CN','Chủ nhiệm lớp',4),('CON','Nữ có con nhỏ < 12 tháng',3),('GV','Giáo viên bộ môn',0),('TP','Tổ phó chuyên môn',1),('TT','Tổ trưởng chuyên môn',3);
/*!40000 ALTER TABLE `dm_chucvu` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `dm_tochuyenmon`
--

LOCK TABLES `dm_tochuyenmon` WRITE;
/*!40000 ALTER TABLE `dm_tochuyenmon` DISABLE KEYS */;
INSERT INTO `dm_tochuyenmon` VALUES ('ANH','Ngoại Ngữ'),('KHTN','Lý - Hóa - Sinh'),('KHXH','Sử - Địa - GDCD'),('TOAN','Toán - Tin'),('VAN','Ngữ Văn'),('VP','Tổ Văn phòng');
/*!40000 ALTER TABLE `dm_tochuyenmon` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `hs_giaovien`
--

LOCK TABLES `hs_giaovien` WRITE;
/*!40000 ALTER TABLE `hs_giaovien` DISABLE KEYS */;
INSERT INTO `hs_giaovien` VALUES ('GV001','Nguyễn Văn An','Nam','1985-04-12','TOAN','Thạc sĩ'),('GV002','Trần Thị Bích Ngọc','Nữ','1992-11-20','VAN','Cử nhân Sư phạm'),('GV003','Lê Hoàng Minh','Nam','1998-08-15','ANH','Cử nhân Sư phạm'),('GV004','Phạm Hồng Loan','Nữ','1988-01-30','KHTN','Thạc sĩ'),('GV005','Nguyễn Thị Lan','Nữ','1994-06-25','KHXH','Cử nhân Sư phạm'),('vvvv','vvvv','Nam','2026-11-07','ANH','Cử nhân Sư phạm');
/*!40000 ALTER TABLE `hs_giaovien` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `qtr_kiemnhiem`
--

LOCK TABLES `qtr_kiemnhiem` WRITE;
/*!40000 ALTER TABLE `qtr_kiemnhiem` DISABLE KEYS */;
INSERT INTO `qtr_kiemnhiem` VALUES ('GV001','CD'),('GV003','CD'),('GV002','CN'),('GV005','CN'),('GV002','CON'),('GV001','TT');
/*!40000 ALTER TABLE `qtr_kiemnhiem` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `taikhoan`
--

LOCK TABLES `taikhoan` WRITE;
/*!40000 ALTER TABLE `taikhoan` DISABLE KEYS */;
INSERT INTO `taikhoan` VALUES ('admin','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','admin'),('gv','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','user'),('user','8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92','user');
/*!40000 ALTER TABLE `taikhoan` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-08 14:43:47
