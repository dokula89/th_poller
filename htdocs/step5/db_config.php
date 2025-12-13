<?php
/**
 * Database configuration for TrustyHousing
 * 
 * NOTE: Direct connection to external DB may fail due to IP restrictions.
 * The PHP files in step5/ need to be deployed to the remote server,
 * or use a local MySQL database with the 'offta' schema.
 */

// External DB connection (Linode server)
define('DB_HOST', '172.104.206.182');
define('DB_PORT', 3306);
define('DB_USER', 'seattlelisted_usr');
define('DB_PASS', 'T@5z6^pl}');
define('DB_NAME', 'offta');

/**
 * Get database connection
 * @return mysqli
 */
function get_db_connection() {
    // Suppress connection errors to handle gracefully
    $conn = @new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT);
    
    if ($conn->connect_error) {
        // Return JSON error instead of dying
        header('Content-Type: application/json');
        echo json_encode([
            'ok' => false,
            'error' => 'Database connection failed: ' . $conn->connect_error,
            'hint' => 'The step5/ PHP files need to be deployed to the remote server, or set up a local MySQL database with the offta schema.',
            'host' => DB_HOST
        ]);
        exit;
    }
    
    $conn->set_charset("utf8mb4");
    return $conn;
}
?>
