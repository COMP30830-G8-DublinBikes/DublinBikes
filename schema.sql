-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: localhost    Database: se_bike
-- ------------------------------------------------------
-- Server version	8.0.43

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
-- Table structure for table `availability`
--

DROP TABLE IF EXISTS `availability`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `availability` (
  `number` int NOT NULL,
  `available_bikes` int DEFAULT NULL,
  `available_bike_stands` int DEFAULT NULL,
  `last_update` datetime NOT NULL,
  `status` varchar(16) DEFAULT NULL,
  `mechanical_bikes` int DEFAULT NULL,
  `electrical_bikes` int DEFAULT NULL,
  `total_bike_stands` int DEFAULT NULL,
  PRIMARY KEY (`number`,`last_update`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `station`
--

DROP TABLE IF EXISTS `station`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `station` (
  `number` int NOT NULL,
  `address` varchar(256) DEFAULT NULL,
  `banking` int DEFAULT NULL,
  `bikestands` int DEFAULT NULL,
  `name` varchar(256) DEFAULT NULL,
  `status` varchar(256) DEFAULT NULL,
  `position_lat` float DEFAULT NULL,
  `position_lng` float DEFAULT NULL,
  `bonus` int DEFAULT NULL,
  `overflow` int DEFAULT NULL,
  PRIMARY KEY (`number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `weather_current`
--

DROP TABLE IF EXISTS `weather_current`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `weather_current` (
  `dt` datetime NOT NULL,
  `temperature` float DEFAULT NULL,
  `feels_like` float DEFAULT NULL,
  `humidity` int DEFAULT NULL,
  `pressure` int DEFAULT NULL,
  `wind_speed` float DEFAULT NULL,
  `cloudiness` int DEFAULT NULL,
  `weather_main` varchar(50) DEFAULT NULL,
  `weather_description` varchar(100) DEFAULT NULL,
  `rain_1h` float DEFAULT NULL,
  `precip_prob` float DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`dt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `weather_daily`
--

DROP TABLE IF EXISTS `weather_daily`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `weather_daily` (
  `dt` datetime NOT NULL,
  `future_date` date NOT NULL,
  `temp_min` float DEFAULT NULL,
  `temp_max` float DEFAULT NULL,
  `humidity` int DEFAULT NULL,
  `pressure` int DEFAULT NULL,
  `wind_speed` float DEFAULT NULL,
  `cloudiness` int DEFAULT NULL,
  `weather_main` varchar(50) DEFAULT NULL,
  `weather_description` varchar(100) DEFAULT NULL,
  `rain` float DEFAULT NULL,
  `precip_prob` float DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`dt`,`future_date`),
  KEY `idx_weather_daily_future_date` (`future_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `weather_hourly`
--

DROP TABLE IF EXISTS `weather_hourly`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `weather_hourly` (
  `dt` datetime NOT NULL,
  `future_dt` datetime NOT NULL,
  `temperature` float DEFAULT NULL,
  `feels_like` float DEFAULT NULL,
  `humidity` int DEFAULT NULL,
  `pressure` int DEFAULT NULL,
  `wind_speed` float DEFAULT NULL,
  `cloudiness` int DEFAULT NULL,
  `weather_main` varchar(50) DEFAULT NULL,
  `weather_description` varchar(100) DEFAULT NULL,
  `rain_1h` float DEFAULT NULL,
  `precip_prob` float DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`dt`,`future_dt`),
  KEY `idx_weather_hourly_future_dt` (`future_dt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-11 17:36:51
