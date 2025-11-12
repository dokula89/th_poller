<?php
try {
    $db = new mysqli('127.0.0.1', 'root', '', 'offta', 3306);
    
    if ($db->connect_errno) {
        echo "Connection failed: " . $db->connect_error . "\n";
        exit(1);
    }
    
    $db->set_charset('utf8mb4');
    
    // Check if table exists
    $res = $db->query("SHOW TABLES LIKE 'api_call_log'");
    
    if ($res && $res->num_rows > 0) {
        echo "✓ Table api_call_log EXISTS\n";
        
        // Count rows
        $count = $db->query("SELECT COUNT(*) as c FROM api_call_log");
        if ($count) {
            $row = $count->fetch_assoc();
            echo "✓ Row count: " . $row['c'] . "\n";
        }
        
        // Show recent entries
        if ($row['c'] > 0) {
            echo "\nRecent entries:\n";
            $recent = $db->query("SELECT endpoint, status, address, created_at FROM api_call_log ORDER BY created_at DESC LIMIT 5");
            while ($entry = $recent->fetch_assoc()) {
                echo "  - {$entry['created_at']}: {$entry['endpoint']} ({$entry['status']}) - {$entry['address']}\n";
            }
        }
    } else {
        echo "✗ Table api_call_log DOES NOT EXIST\n";
        echo "Creating table now...\n";
        
        $sql = "CREATE TABLE IF NOT EXISTS api_call_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            endpoint VARCHAR(64) NOT NULL,
            status VARCHAR(64) NULL,
            url TEXT NULL,
            address TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_created_at (created_at),
            INDEX idx_endpoint (endpoint),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
        
        if ($db->query($sql)) {
            echo "✓ Table created successfully\n";
        } else {
            echo "✗ Failed to create table: " . $db->error . "\n";
        }
    }
    
    $db->close();
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
