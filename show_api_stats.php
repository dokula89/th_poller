<?php
try {
    $db = new mysqli('127.0.0.1', 'root', '', 'offta', 3306);
    
    if ($db->connect_errno) {
        echo "Connection failed: " . $db->connect_error . "\n";
        exit(1);
    }
    
    $db->set_charset('utf8mb4');
    
    // Get today's count
    $today = $db->query("SELECT COUNT(*) as c FROM api_call_log WHERE DATE(created_at) = CURDATE()");
    $today_count = $today->fetch_assoc()['c'];
    
    // Get last 7 days count
    $week = $db->query("SELECT COUNT(*) as c FROM api_call_log WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)");
    $week_count = $week->fetch_assoc()['c'];
    
    // Get last 30 days count
    $month = $db->query("SELECT COUNT(*) as c FROM api_call_log WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)");
    $month_count = $month->fetch_assoc()['c'];
    
    echo "API Call Statistics:\n";
    echo "═══════════════════\n";
    echo "Today:        {$today_count}\n";
    echo "Last 7 days:  {$week_count}\n";
    echo "Last 30 days: {$month_count}\n";
    echo "\nAll entries by date:\n";
    echo "───────────────────\n";
    
    $by_date = $db->query("SELECT DATE(created_at) as day, COUNT(*) as c FROM api_call_log GROUP BY day ORDER BY day DESC LIMIT 10");
    while ($row = $by_date->fetch_assoc()) {
        echo "{$row['day']}: {$row['c']} calls\n";
    }
    
    $db->close();
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
