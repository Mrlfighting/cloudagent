-- ==========================================================
-- äº‘å¹³å°ç”¨æˆ·ã€è®¢å•ã€å®žä¾‹ã€ç›‘æŽ§ä¸ŽèŠå¤©ç³»ç»Ÿåˆå§‹åŒ–è„šæœ¬
-- å­—ç¬¦é›†ç»Ÿä¸€ä½¿ç”¨ utf8mb4ï¼Œé¿å…ä¸­æ–‡è¢«å†™æˆ ????
-- ==========================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS cloud_platform DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cloud_platform;

CREATE TABLE IF NOT EXISTS cloud_orders (
    order_id VARCHAR(50) PRIMARY KEY COMMENT 'è®¢å•å”¯ä¸€ID',
    user_id VARCHAR(50) NOT NULL COMMENT 'ç”¨æˆ·ID',
    product_name VARCHAR(100) NOT NULL COMMENT 'äº§å“åç§°',
    billing_mode VARCHAR(20) NOT NULL COMMENT 'è®¡è´¹æ¨¡å¼',
    amount DECIMAL(10, 2) NOT NULL COMMENT 'è®¢å•é‡‘é¢',
    status VARCHAR(20) NOT NULL COMMENT 'è®¢å•çŠ¶æ€',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'åˆ›å»ºæ—¶é—´',
    INDEX idx_cloud_orders_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='äº‘äº§å“è®¢å•è¡¨';

TRUNCATE TABLE cloud_orders;
INSERT INTO cloud_orders (order_id, user_id, product_name, billing_mode, amount, status, created_at) VALUES
('ORD-1001-001', 'user_1001', 'ecs.g8a.4xlarge', 'åŒ…å¹´åŒ…æœˆ', 12500.00, 'Paid', '2023-10-01 10:00:00'),
('ORD-1001-002', 'user_1001', 'rds.mysql.c1.large', 'åŒ…å¹´åŒ…æœˆ', 3600.00, 'Paid', '2023-10-05 14:30:00'),
('ORD-1001-003', 'user_1001', 'å…±äº«å¸¦å®½ 100Mbps', 'æŒ‰é‡ä»˜è´¹', 150.50, 'Paid', '2023-11-01 08:15:00'),
('ORD-1002-001', 'user_1002', 'ecs.c7.large', 'æŒ‰é‡ä»˜è´¹', 45.20, 'Paid', '2023-11-15 09:00:00'),
('ORD-1002-002', 'user_1002', 'äº‘ç›˜ ESSD PL0 40G', 'åŒ…å¹´åŒ…æœˆ', 120.00, 'Paid', '2023-11-15 09:05:00'),
('ORD-1002-003', 'user_1002', 'ecs.c7.large', 'æŒ‰é‡ä»˜è´¹', 12.80, 'Unpaid', '2023-11-16 10:00:00');

CREATE TABLE IF NOT EXISTS cloud_instances (
    instance_id VARCHAR(50) PRIMARY KEY COMMENT 'å®žä¾‹å”¯ä¸€ID',
    user_id VARCHAR(50) NOT NULL COMMENT 'æ‰€å±žç”¨æˆ·',
    order_id VARCHAR(50) NOT NULL COMMENT 'å…³è”è®¢å•',
    instance_type VARCHAR(100) NOT NULL COMMENT 'å®žä¾‹è§„æ ¼',
    region_id VARCHAR(50) NOT NULL COMMENT 'åœ°åŸŸ',
    zone_id VARCHAR(50) NOT NULL COMMENT 'å¯ç”¨åŒº',
    status VARCHAR(20) NOT NULL COMMENT 'è¿è¡ŒçŠ¶æ€',
    public_ip VARCHAR(20) COMMENT 'å…¬ç½‘IP',
    INDEX idx_cloud_instances_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='äº‘èµ„æºå®žä¾‹è¡¨';

TRUNCATE TABLE cloud_instances;
INSERT INTO cloud_instances (instance_id, user_id, order_id, instance_type, region_id, zone_id, status, public_ip) VALUES
('i-bp1_user1001_ecs', 'user_1001', 'ORD-1001-001', 'ecs.g8a.4xlarge', 'cn-beijing', 'cn-beijing-k', 'Running', '47.100.1.1'),
('rm-bp1_user1001_rds', 'user_1001', 'ORD-1001-002', 'rds.mysql.c1.large', 'cn-beijing', 'cn-beijing-l', 'Running', NULL),
('i-bp1_user1002_ecs', 'user_1002', 'ORD-1002-001', 'ecs.c7.large', 'cn-hangzhou', 'cn-hangzhou-h', 'Stopped', '114.55.2.2');

CREATE TABLE IF NOT EXISTS instance_metrics_daily (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'è‡ªå¢žä¸»é”®',
    instance_id VARCHAR(50) NOT NULL COMMENT 'å®žä¾‹ID',
    user_id VARCHAR(50) NOT NULL COMMENT 'æ‰€å±žç”¨æˆ·ID',
    metric_date DATE NOT NULL COMMENT 'ç»Ÿè®¡æ—¥æœŸ',
    avg_cpu_usage_percent DECIMAL(5,2) NOT NULL COMMENT 'å¹³å‡CPUåˆ©ç”¨çŽ‡',
    avg_memory_usage_percent DECIMAL(5,2) NOT NULL COMMENT 'å¹³å‡å†…å­˜åˆ©ç”¨çŽ‡',
    max_network_out_mbps DECIMAL(8,2) NOT NULL COMMENT 'å‡ºå£å¸¦å®½å³°å€¼',
    INDEX idx_instance_date (instance_id, metric_date),
    INDEX idx_user_instance (user_id, instance_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='å®žä¾‹æ—¥çº§ç›‘æŽ§æŒ‡æ ‡è¡¨';

TRUNCATE TABLE instance_metrics_daily;
INSERT INTO instance_metrics_daily (instance_id, user_id, metric_date, avg_cpu_usage_percent, avg_memory_usage_percent, max_network_out_mbps) VALUES
('i-bp1_user1001_ecs', 'user_1001', DATE_SUB(CURDATE(), INTERVAL 6 DAY), 2.10, 18.50, 1.20),
('i-bp1_user1001_ecs', 'user_1001', DATE_SUB(CURDATE(), INTERVAL 5 DAY), 2.50, 19.10, 1.60),
('i-bp1_user1001_ecs', 'user_1001', DATE_SUB(CURDATE(), INTERVAL 4 DAY), 3.20, 20.40, 2.00),
('i-bp1_user1001_ecs', 'user_1001', DATE_SUB(CURDATE(), INTERVAL 3 DAY), 1.90, 17.90, 1.00),
('i-bp1_user1001_ecs', 'user_1001', DATE_SUB(CURDATE(), INTERVAL 2 DAY), 2.80, 18.20, 1.40),
('i-bp1_user1001_ecs', 'user_1001', DATE_SUB(CURDATE(), INTERVAL 1 DAY), 2.40, 19.00, 1.30),
('i-bp1_user1001_ecs', 'user_1001', CURDATE(), 2.00, 18.70, 1.10),
('i-bp1_user1002_ecs', 'user_1002', DATE_SUB(CURDATE(), INTERVAL 6 DAY), 36.50, 62.10, 42.00),
('i-bp1_user1002_ecs', 'user_1002', DATE_SUB(CURDATE(), INTERVAL 5 DAY), 41.20, 65.00, 51.00),
('i-bp1_user1002_ecs', 'user_1002', DATE_SUB(CURDATE(), INTERVAL 4 DAY), 38.40, 63.50, 48.00),
('i-bp1_user1002_ecs', 'user_1002', DATE_SUB(CURDATE(), INTERVAL 3 DAY), 44.00, 67.30, 55.00),
('i-bp1_user1002_ecs', 'user_1002', DATE_SUB(CURDATE(), INTERVAL 2 DAY), 39.10, 60.80, 47.00),
('i-bp1_user1002_ecs', 'user_1002', DATE_SUB(CURDATE(), INTERVAL 1 DAY), 42.80, 64.20, 53.00),
('i-bp1_user1002_ecs', 'user_1002', CURDATE(), 40.30, 61.90, 49.00);

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY COMMENT 'ç”¨æˆ·ID',
    username VARCHAR(80) NOT NULL UNIQUE COMMENT 'ç™»å½•ç”¨æˆ·å',
    display_name VARCHAR(100) NOT NULL COMMENT 'æ˜¾ç¤ºåç§°',
    password_hash VARCHAR(255) NOT NULL COMMENT 'å¯†ç å“ˆå¸Œ',
    disabled TINYINT NOT NULL DEFAULT 0 COMMENT 'æ˜¯å¦ç¦ç”¨',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ç³»ç»Ÿç”¨æˆ·è¡¨';

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(80) PRIMARY KEY COMMENT 'ä¼šè¯ID',
    user_id VARCHAR(50) NOT NULL COMMENT 'æ‰€å±žç”¨æˆ·',
    title VARCHAR(100) NOT NULL DEFAULT 'æ–°å¯¹è¯' COMMENT 'ä¼šè¯æ ‡é¢˜',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL COMMENT 'è½¯åˆ é™¤æ—¶é—´',
    INDEX idx_chat_sessions_user_updated (user_id, deleted_at, updated_at),
    CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='èŠå¤©ä¼šè¯è¡¨';

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(80) NOT NULL COMMENT 'ä¼šè¯ID',
    user_id VARCHAR(50) NOT NULL COMMENT 'æ‰€å±žç”¨æˆ·',
    role VARCHAR(20) NOT NULL COMMENT 'user/assistant',
    content MEDIUMTEXT NOT NULL COMMENT 'æ¶ˆæ¯å†…å®¹',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chat_messages_session_id (session_id, id),
    INDEX idx_chat_messages_user_id (user_id, created_at),
    CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id),
    CONSTRAINT fk_chat_messages_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='èŠå¤©æ¶ˆæ¯è¡¨';

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    token_hash CHAR(64) NOT NULL UNIQUE COMMENT 'åˆ·æ–°ä»¤ç‰ŒSHA256',
    user_id VARCHAR(50) NOT NULL COMMENT 'æ‰€å±žç”¨æˆ·',
    expires_at DATETIME NOT NULL COMMENT 'è¿‡æœŸæ—¶é—´',
    revoked_at DATETIME NULL COMMENT 'æ’¤é”€æ—¶é—´',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_refresh_tokens_user_id (user_id),
    INDEX idx_refresh_tokens_expires_at (expires_at),
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='åˆ·æ–°ä»¤ç‰Œè¡¨';
CREATE TABLE IF NOT EXISTS agent_call_traces (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    trace_id VARCHAR(80) NOT NULL UNIQUE COMMENT '调用轨迹ID',
    user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
    session_id VARCHAR(80) NOT NULL COMMENT '会话ID',
    query MEDIUMTEXT NOT NULL COMMENT '用户问题',
    status VARCHAR(40) NOT NULL COMMENT '当前状态',
    route_agent VARCHAR(80) NULL COMMENT '命中的Agent或缓存',
    stages JSON NULL COMMENT '阶段状态列表',
    duration_ms INT NULL COMMENT '总耗时毫秒',
    error_message TEXT NULL COMMENT '失败原因',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_agent_traces_user_created (user_id, created_at),
    INDEX idx_agent_traces_session_created (session_id, created_at),
    INDEX idx_agent_traces_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent调用轨迹表';