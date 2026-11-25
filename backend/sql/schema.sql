-- MySQL 8.0.16+ / InnoDB / utf8mb4. Times are ISO-8601 strings matching the HTTP API.

CREATE TABLE IF NOT EXISTS `factories` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `city` VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `users` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `username` VARCHAR(100) UNIQUE NOT NULL,
  `password` VARCHAR(180) NOT NULL,
  `name` VARCHAR(255),
  `role` VARCHAR(32),
  `factory_id` INT,
  `active` INT DEFAULT 1,
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `sessions` (
  `token` VARCHAR(100) PRIMARY KEY,
  `user_id` INT,
  `csrf` VARCHAR(100),
  `expires` DOUBLE,
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `devices` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `code` VARCHAR(100) UNIQUE,
  `name` VARCHAR(255),
  `line` VARCHAR(255),
  `status` VARCHAR(40),
  `temperature` DOUBLE,
  `pressure` DOUBLE,
  `vibration` DOUBLE,
  `runtime` INT,
  `updated_at` VARCHAR(32),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `readings` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `device_id` INT,
  `temperature` DOUBLE,
  `pressure` DOUBLE,
  `vibration` DOUBLE,
  `created_at` VARCHAR(32),
  FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`),
  KEY `reading_device_time` (`device_id`,`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `orders` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `code` VARCHAR(100) UNIQUE,
  `product` VARCHAR(300),
  `batch` VARCHAR(300),
  `quantity` INT CHECK(quantity>0),
  `completed` INT DEFAULT 0,
  `status` VARCHAR(40),
  `priority` VARCHAR(40),
  `due_date` VARCHAR(32),
  `device_id` INT,
  `created_at` VARCHAR(32),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`),
  FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`),
  CHECK(completed>=0 AND completed<=quantity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `production_reports` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `order_id` INT,
  `quantity` INT,
  `user_id` INT,
  `created_at` VARCHAR(32),
  FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `quality` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `order_id` INT,
  `batch` VARCHAR(300),
  `sample_size` INT CHECK(sample_size>0),
  `defects` INT,
  `defect_type` VARCHAR(300),
  `inspector` VARCHAR(255),
  `created_at` VARCHAR(32),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`),
  FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  CHECK(defects>=0 AND defects<=sample_size)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `anomalies` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `device_id` INT,
  `order_id` INT,
  `title` VARCHAR(300),
  `severity` LONGTEXT,
  `status` VARCHAR(40) DEFAULT '待分析',
  `description` LONGTEXT,
  `source` VARCHAR(300),
  `created_at` VARCHAR(32),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`),
  FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`),
  FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `analyses` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `anomaly_id` INT,
  `result` LONGTEXT,
  `created_at` VARCHAR(32),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`),
  FOREIGN KEY (`anomaly_id`) REFERENCES `anomalies` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `tasks` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `anomaly_id` INT,
  `analysis_id` INT,
  `title` VARCHAR(300),
  `action` VARCHAR(2000),
  `assignee` INT,
  `status` VARCHAR(40),
  `priority` VARCHAR(40),
  `note` LONGTEXT DEFAULT (''),
  `review_note` LONGTEXT DEFAULT (''),
  `sample_size` INT,
  `defects` INT,
  `version` INT DEFAULT 1,
  `created_at` VARCHAR(32),
  `updated_at` VARCHAR(32),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`),
  FOREIGN KEY (`anomaly_id`) REFERENCES `anomalies` (`id`),
  FOREIGN KEY (`analysis_id`) REFERENCES `analyses` (`id`),
  FOREIGN KEY (`assignee`) REFERENCES `users` (`id`),
  `active_anomaly_id` INT GENERATED ALWAYS AS (CASE WHEN `status` <> '已关闭' THEN `anomaly_id` ELSE NULL END) STORED,
  UNIQUE KEY `task_one_active` (`active_anomaly_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `task_events` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `task_id` INT,
  `user_name` VARCHAR(255),
  `action` VARCHAR(2000),
  `note` LONGTEXT,
  `created_at` VARCHAR(32),
  FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `attachments` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `task_id` INT,
  `filename` VARCHAR(150) UNIQUE,
  `original_name` VARCHAR(300),
  `mime` VARCHAR(100),
  `created_at` VARCHAR(32),
  FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `materials` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `code` VARCHAR(100) UNIQUE,
  `name` VARCHAR(255),
  `spec` VARCHAR(300),
  `unit` VARCHAR(40),
  `stock` DOUBLE CHECK(stock>=0),
  `min_stock` DOUBLE,
  `location` VARCHAR(300),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `stock_moves` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `material_id` INT,
  `direction` VARCHAR(20),
  `quantity` DOUBLE,
  `note` LONGTEXT,
  `user_name` VARCHAR(255),
  `created_at` VARCHAR(32),
  FOREIGN KEY (`material_id`) REFERENCES `materials` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `samples` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `temp` INT,
  `pressure` INT,
  `wear` INT,
  `material` INT,
  `product` INT,
  `defect` INT,
  `source` VARCHAR(300),
  `created_at` VARCHAR(32),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `training_jobs` (
  `id` VARCHAR(64) PRIMARY KEY,
  `status` VARCHAR(40),
  `round` INT DEFAULT 0,
  `total_rounds` INT,
  `config` LONGTEXT,
  `history` LONGTEXT DEFAULT ('[]'),
  `result` LONGTEXT DEFAULT ('{}'),
  `error` LONGTEXT DEFAULT (''),
  `created_at` VARCHAR(32),
  `updated_at` VARCHAR(32)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `node_status` (
  `factory_id` INT PRIMARY KEY,
  `enabled` INT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `audit` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `user_name` VARCHAR(255),
  `action` VARCHAR(2000),
  `entity` VARCHAR(100),
  `detail` LONGTEXT,
  `factory_id` INT,
  `created_at` VARCHAR(32)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `idempotency` (
  `user_id` INT,
  `key` VARCHAR(128),
  `path` VARCHAR(255),
  `response` LONGTEXT,
  `created_at` VARCHAR(32),
  PRIMARY KEY (`user_id`, `key`, `path`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `source_records` (
  `source_key` VARCHAR(80),
  `entity` VARCHAR(100),
  `original_id` VARCHAR(100),
  `record_id` INT,
  `factory_id` INT,
  `label` VARCHAR(300),
  `sha256` VARCHAR(64),
  `original_status` VARCHAR(100),
  `imported_at` VARCHAR(32),
  PRIMARY KEY (`source_key`, `entity`, `original_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `training_events` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `job_id` VARCHAR(64),
  `round` INT,
  `factory_id` INT,
  `phase` VARCHAR(40),
  `detail` LONGTEXT,
  `created_at` VARCHAR(32),
  FOREIGN KEY (`job_id`) REFERENCES `training_jobs` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `assistant_messages` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `user_id` INT,
  `factory_id` INT,
  `question` LONGTEXT,
  `response` LONGTEXT,
  `created_at` VARCHAR(32),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS `demo_runs` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `factory_id` INT,
  `device_id` INT,
  `order_id` INT,
  `material_id` INT,
  `user_id` INT,
  `running` INT DEFAULT 0,
  `tick` INT DEFAULT 0,
  `scenario` VARCHAR(40) DEFAULT 'normal',
  `reason` VARCHAR(1000) DEFAULT '',
  `started_at` VARCHAR(32),
  `updated_at` VARCHAR(32),
  `state` LONGTEXT NOT NULL DEFAULT ('{}'),
  FOREIGN KEY (`factory_id`) REFERENCES `factories` (`id`),
  FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`),
  FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`),
  FOREIGN KEY (`material_id`) REFERENCES `materials` (`id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  KEY `demo_factory` (`factory_id`,`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;
