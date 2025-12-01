<?php
/**
 * Track API usage for Google APIs
 * Logs all API calls to database for expense tracking
 */

// Pricing constants (as of 2025)
$GOOGLE_PRICING = [
    'places_details' => 0.017,
    'geocoding' => 0.005,
    'places_search' => 0.032,
    'places_nearby' => 0.032,
];

/**
 * Log a Google API call to the database
 * 
 * @param mysqli $mysqli Database connection
 * @param string $endpoint API endpoint (e.g., 'places_details', 'geocoding')
 * @param int $calls_count Number of API calls made (default: 1)
 * @param array|null $metadata Optional metadata as associative array
 * @return float Total cost in USD
 */
function log_google_api_call($mysqli, $endpoint, $calls_count = 1, $metadata = null) {
    global $GOOGLE_PRICING;
    
    try {
        // Calculate cost
        $cost_per_call = $GOOGLE_PRICING[$endpoint] ?? 0.01;
        $total_cost = $cost_per_call * $calls_count;
        
        // Ensure api_calls table exists
        $mysqli->query("
            CREATE TABLE IF NOT EXISTS api_calls (
                id INT AUTO_INCREMENT PRIMARY KEY,
                service VARCHAR(50) NOT NULL,
                endpoint VARCHAR(100) NOT NULL,
                call_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tokens_used INT DEFAULT 0,
                calls_count INT DEFAULT 1,
                input_tokens INT DEFAULT 0,
                output_tokens INT DEFAULT 0,
                model VARCHAR(50),
                cost_usd DECIMAL(10, 6) DEFAULT 0,
                metadata TEXT,
                INDEX idx_service (service),
                INDEX idx_call_time (call_time)
            )
        ");
        
        // Prepare metadata
        $metadata_json = $metadata ? json_encode($metadata) : null;
        
        // Insert record
        $stmt = $mysqli->prepare("
            INSERT INTO api_calls 
            (service, endpoint, calls_count, cost_usd, metadata)
            VALUES (?, ?, ?, ?, ?)
        ");
        
        $service = 'google';
        $stmt->bind_param('ssids', $service, $endpoint, $calls_count, $total_cost, $metadata_json);
        $stmt->execute();
        $stmt->close();
        
        error_log("[API Track] Google $endpoint: $calls_count calls (\$$total_cost)");
        return $total_cost;
        
    } catch (Exception $e) {
        error_log("[API Track] Error logging Google call: " . $e->getMessage());
        return 0;
    }
}

/**
 * Get total costs for all API services
 * 
 * @param mysqli $mysqli Database connection
 * @return array Associative array with service costs
 */
function get_total_api_costs($mysqli) {
    try {
        $result = $mysqli->query("
            SELECT 
                service,
                SUM(cost_usd) as total_cost,
                COUNT(*) as total_calls
            FROM api_calls
            GROUP BY service
        ");
        
        $costs = [
            'openai' => ['cost' => 0, 'calls' => 0],
            'google' => ['cost' => 0, 'calls' => 0]
        ];
        
        while ($row = $result->fetch_assoc()) {
            $service = $row['service'];
            if (isset($costs[$service])) {
                $costs[$service]['cost'] = (float)$row['total_cost'];
                $costs[$service]['calls'] = (int)$row['total_calls'];
            }
        }
        
        return $costs;
        
    } catch (Exception $e) {
        error_log("[API Track] Error getting total costs: " . $e->getMessage());
        return [
            'openai' => ['cost' => 0, 'calls' => 0],
            'google' => ['cost' => 0, 'calls' => 0]
        ];
    }
}
