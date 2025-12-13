<?php
/**
 * Single database connection point for all PHP scripts
 * Include this file once at the top of any script that needs DB access
 * 
 * Usage: require_once __DIR__ . '/db_connection.php';
 * Then use: $db or get_shared_db()
 */

// Prevent multiple connections
if (!isset($GLOBALS['_db_connection_initialized'])) {
    $GLOBALS['_db_connection_initialized'] = true;
    
    // External DB config (Linode server)
    define('DB_HOST', '172.104.206.182');
    define('DB_PORT', 3306);
    define('DB_USER', 'seattlelisted_usr');
    define('DB_PASS', 'T@5z6^pl}');
    define('DB_NAME', 'offta');
    
    // Create and store single connection
    $GLOBALS['_shared_db'] = null;
    
    /**
     * Get the shared database connection (creates if not exists)
     * @return mysqli|null
     */
    function get_shared_db() {
        if ($GLOBALS['_shared_db'] === null) {
            $conn = @new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT);
            if ($conn->connect_errno) {
                error_log("DB connection failed: " . $conn->connect_error);
                return null;
            }
            $conn->set_charset('utf8mb4');
            $GLOBALS['_shared_db'] = $conn;
        }
        return $GLOBALS['_shared_db'];
    }
    
    // Auto-initialize connection
    $db = get_shared_db();
    
    /**
     * Output JSON response and exit
     */
    function out_json($arr, $code = 200) {
        http_response_code($code);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($arr, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        exit;
    }
    
    /**
     * Set no-cache headers to prevent API caching
     */
    function _no_cache_headers() {
        header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
        header('Pragma: no-cache');
        header('Expires: Thu, 01 Jan 1970 00:00:00 GMT');
    }
}
