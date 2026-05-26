-- ============================================================
-- Schema creation
-- ============================================================

CREATE TABLE user (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(255) NOT NULL,
    country VARCHAR(255) NOT NULL,
    city VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id)
);


CREATE TABLE item (
    id INT NOT NULL AUTO_INCREMENT,
    item_name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id)
);


CREATE TABLE user_order (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    shipping_address VARCHAR(255) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    status ENUM('TEMP', 'CLOSE') NOT NULL DEFAULT 'TEMP',
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);


CREATE TABLE user_favorite (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    item_id INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_item (user_id, item_id),
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (item_id) REFERENCES item(id)
);


CREATE TABLE order_item (
    order_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    price DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, item_id),
    FOREIGN KEY (order_id) REFERENCES user_order(id),
    FOREIGN KEY (item_id) REFERENCES item(id)
);


-- ============================================================
-- Seed data
-- ============================================================

-- ------------------------------------------------------------
-- Users
-- All seed users share the same password for development: Password123
-- The hash below was generated with passlib bcrypt (CryptContext schemes=["bcrypt"])
-- ------------------------------------------------------------
-- country uses ISO codes (see model/user_request.py SUPPORTED_COUNTRIES).
INSERT INTO user (username, first_name, last_name, email, phone, country, city, hashed_password, is_active) VALUES
('yossi_active',    'Yossi', 'Cohen',    'yossi@example.com',  '050-1111111', 'IL', 'Tel Aviv',  '$2b$12$zqeCRnCK8hOXVGWcC7Vyz.T7O7QE82r6P5MDqAdOrI7I7nUghq1W.', TRUE),
('sara_active',     'Sara',  'Levi',     'sara@example.com',   '052-2222222', 'IL', 'Jerusalem', '$2b$12$zqeCRnCK8hOXVGWcC7Vyz.T7O7QE82r6P5MDqAdOrI7I7nUghq1W.', TRUE),
('deleted_user',    'David', 'Mizrahi',  'david@example.com',  '054-3333333', 'IL', 'Haifa',     '$2b$12$zqeCRnCK8hOXVGWcC7Vyz.T7O7QE82r6P5MDqAdOrI7I7nUghq1W.', FALSE);


-- 30 items aligned 1:1 by id with the recommender catalog (ml/notebooks/recommender.ipynb).
-- 3 items left at stock=0 (#9, #13, #28) to exercise the out-of-stock UI path.
INSERT INTO item (item_name, price, stock) VALUES
('Headphones',          89.00,  30),   -- 1   Tech
('Laptop',             899.00,  20),   -- 2   Tech
('Smartwatch',         249.00,  25),   -- 3   Tech
('Bluetooth Speaker',   69.00,  40),   -- 4   Tech
('Tablet',             399.00,  18),   -- 5   Tech
('Wireless Mouse',      29.00,  60),   -- 6   Tech
('Coffee Maker',       149.00,  35),   -- 7   Kitchen
('Blender',             69.00,  40),   -- 8   Kitchen
('Air Fryer',          129.00,   0),   -- 9   Kitchen  (out of stock)
('Knife Set',           99.00,  30),   -- 10  Kitchen
('Mixer',              179.00,  20),   -- 11  Kitchen
('Toaster',             39.00,  50),   -- 12  Kitchen
('T-Shirt',             19.00,   0),   -- 13  Fashion  (out of stock)
('Jeans',               59.00,  70),   -- 14  Fashion
('Sneakers',            89.00,  50),   -- 15  Fashion
('Jacket',             149.00,  35),   -- 16  Fashion
('Cap',                 19.00, 100),   -- 17  Fashion
('Belt',                39.00,  80),   -- 18  Fashion
('Lamp',                39.00,  60),   -- 19  Home
('Pillow',              19.00,  90),   -- 20  Home
('Bedsheet',            49.00,  55),   -- 21  Home
('Candle',              14.00, 120),   -- 22  Home
('Curtains',            79.00,  40),   -- 23  Home
('Vase',                29.00,  65),   -- 24  Home
('Yoga Mat',            39.00,  45),   -- 25  Sports
('Dumbbells',           79.00,  30),   -- 26  Sports
('Running Shoes',       99.00,  40),   -- 27  Sports
('Sports Bottle',       15.00,   0),   -- 28  Sports  (out of stock)
('Backpack',            59.00,  50),   -- 29  Sports
('Resistance Band',     25.00,  80);   -- 30  Sports


-- Favorites: Yossi leans Tech, Sara leans Home/Kitchen — gives the
-- recommender a clear persona signal to pick up in the demo.
INSERT INTO user_favorite (user_id, item_id) VALUES
(1,  1),   -- Yossi -> Headphones    (Tech)
(1,  2),   -- Yossi -> Laptop        (Tech)
(1,  3),   -- Yossi -> Smartwatch    (Tech)
(2,  7),   -- Sara  -> Coffee Maker  (Kitchen)
(2, 19),   -- Sara  -> Lamp          (Home)
(2, 22);   -- Sara  -> Candle        (Home)


-- ------------------------------------------------------------
-- Orders
-- Yossi (id=1): 1 CLOSE order (Tech) + 1 TEMP order (Tech cart in progress)
-- Sara  (id=2): 1 CLOSE order (Kitchen)
-- ------------------------------------------------------------
INSERT INTO user_order (id, user_id, created_at, shipping_address, total_price, status) VALUES
(1, 1, '2026-04-10 14:30:00', 'Herzl 12, Tel Aviv',       98.00, 'CLOSE'),
(2, 1, '2026-05-15 09:00:00', 'Herzl 12, Tel Aviv',      399.00, 'TEMP'),
(3, 2, '2026-05-01 16:45:00', 'King George 5, Jerusalem', 218.00, 'CLOSE');


-- ------------------------------------------------------------
-- Order items
-- ------------------------------------------------------------
INSERT INTO order_item (order_id, item_id, quantity, price) VALUES
-- Yossi's CLOSE order (id=1): 1 x Bluetooth Speaker + 1 x Wireless Mouse = 69 + 29 = 98
(1, 4, 1,  69.00),
(1, 6, 1,  29.00),

-- Yossi's TEMP order (id=2): 1 x Tablet = 399
(2, 5, 1, 399.00),

-- Sara's CLOSE order (id=3): 1 x Mixer + 1 x Toaster = 179 + 39 = 218
(3, 11, 1, 179.00),
(3, 12, 1,  39.00);
