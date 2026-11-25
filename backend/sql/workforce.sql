-- Additive personnel schema. Clock times use the factory's Asia/Shanghai local time.
CREATE TABLE IF NOT EXISTS staff_employees (
 id INT PRIMARY KEY AUTO_INCREMENT,
 factory_id INT NOT NULL,
 user_id INT UNIQUE,
 code VARCHAR(40) NOT NULL,
 name VARCHAR(80) NOT NULL,
 workshop VARCHAR(80) NOT NULL,
 position VARCHAR(80) NOT NULL,
 team VARCHAR(80) NOT NULL,
 skills TEXT NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT '在职',
 version INT NOT NULL DEFAULT 1,
 created_at VARCHAR(32) NOT NULL,
 UNIQUE KEY employee_code(factory_id,code),
 FOREIGN KEY(factory_id) REFERENCES factories(id),
 FOREIGN KEY(user_id) REFERENCES users(id),
 CHECK(status IN ('在职','停用'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS staff_shifts (
 id INT PRIMARY KEY AUTO_INCREMENT,
 factory_id INT NOT NULL,
 name VARCHAR(80) NOT NULL,
 start_time VARCHAR(5) NOT NULL,
 end_time VARCHAR(5) NOT NULL,
 version INT NOT NULL DEFAULT 1,
 UNIQUE KEY shift_name(factory_id,name),
 FOREIGN KEY(factory_id) REFERENCES factories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS staff_plans (
 id INT PRIMARY KEY AUTO_INCREMENT,
 factory_id INT NOT NULL,
 shift_id INT NOT NULL,
 work_date VARCHAR(10) NOT NULL,
 line VARCHAR(80) NOT NULL,
 start_at VARCHAR(32) NOT NULL,
 end_at VARCHAR(32) NOT NULL,
 required_count INT NOT NULL,
 required_skill VARCHAR(40) NOT NULL DEFAULT '',
 note VARCHAR(500) NOT NULL DEFAULT '',
 status VARCHAR(20) NOT NULL DEFAULT '已发布',
 version INT NOT NULL DEFAULT 1,
 created_at VARCHAR(32) NOT NULL,
 KEY plan_factory_time(factory_id,start_at,end_at),
 FOREIGN KEY(factory_id) REFERENCES factories(id),
 FOREIGN KEY(shift_id) REFERENCES staff_shifts(id),
 CHECK(required_count BETWEEN 1 AND 100),
 CHECK(status IN ('已发布','已取消'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS staff_assignments (
 id INT PRIMARY KEY AUTO_INCREMENT,
 plan_id INT NOT NULL,
 employee_id INT NOT NULL,
 UNIQUE KEY plan_employee(plan_id,employee_id),
 KEY employee_plan(employee_id,plan_id),
 FOREIGN KEY(plan_id) REFERENCES staff_plans(id),
 FOREIGN KEY(employee_id) REFERENCES staff_employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE IF NOT EXISTS staff_leaves (
 id INT PRIMARY KEY AUTO_INCREMENT,
 factory_id INT NOT NULL,
 employee_id INT NOT NULL,
 start_at VARCHAR(32) NOT NULL,
 end_at VARCHAR(32) NOT NULL,
 reason VARCHAR(500) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT '待审批',
 review_note VARCHAR(500) NOT NULL DEFAULT '',
 reviewer_id INT,
 version INT NOT NULL DEFAULT 1,
 created_at VARCHAR(32) NOT NULL,
 KEY leave_employee_time(employee_id,start_at,end_at),
 FOREIGN KEY(factory_id) REFERENCES factories(id),
 FOREIGN KEY(employee_id) REFERENCES staff_employees(id),
 FOREIGN KEY(reviewer_id) REFERENCES users(id),
 CHECK(status IN ('待审批','已批准','已驳回','已撤销'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;
