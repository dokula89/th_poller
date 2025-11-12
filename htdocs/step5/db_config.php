<?php
/**
 * Database configuration for TrustyHousing
 * Using LOCAL MySQL for better performance
 */

define('DB_HOST', '127.0.0.1');
define('DB_PORT', 3306);
define('DB_USER', 'local_uzr');
define('DB_PASS', 'fuck');
define('DB_NAME', 'offta');

/**
 * Get database connection
 * @return mysqli
 */
function get_db_connection() {
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT);
    
    if ($conn->connect_error) {
        die("Connection failed: " . $conn->connect_error);
    }
    
    $conn->set_charset("utf8mb4");
    return $conn;
}
?>
