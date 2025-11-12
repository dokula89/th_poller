<?php
/**
 * Queue Step API
 * 
 * Updates the status of individual steps for queue jobs
 * Used by the Python step-by-step workflow UI
 * 
 * POST /queue_step_api.php
 * Body: {
 *   "table": "queue_websites",
 *   "id": 123,
 *   "step": "capture_html",
 *   "status": "running|done|error|pending",
 *   "message": "Optional message",
 *   "timestamp": "2025-10-30 12:34:56"
 * }
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Database configuration
$DB_HOST = '172.104.206.182';
$DB_PORT = 3306;
$DB_NAME = 'offta';
$DB_USER = 'seattlelisted_usr';
$DB_PASS = 'Seattlelisted2024!';

// Allowed tables (whitelist for security)
$ALLOWED_TABLES = [
    'queue_websites',
    'listing_networks',
    'parcel',
    'code',
    '911'
];

// Allowed steps
$ALLOWED_STEPS = [
    'capture_html',
    'create_json',
    'manual_match',
    'process_db',
    'rename_images'
];

// Allowed statuses
$ALLOWED_STATUSES = [
    'pending',
    'running',
    'done',
    'error'
];

/**
 * Send JSON response and exit
 */
function send_response($ok, $data = null, $error = null) {
    $response = ['ok' => $ok];
    if ($data !== null) {
        $response['data'] = $data;
    }
    if ($error !== null) {
        $response['error'] = $error;
    }
    echo json_encode($response);
    exit();
}

/**
 * Log error for debugging
 */
function log_error($message) {
    error_log("[Queue Step API] " . $message);
}

// Only accept POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_response(false, null, 'Only POST requests are allowed');
}

// Get POST data (JSON)
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    send_response(false, null, 'Invalid JSON input');
}

// Validate required fields
$table = $data['table'] ?? null;
$id = $data['id'] ?? null;
$step = $data['step'] ?? null;
$status = $data['status'] ?? null;
$message = $data['message'] ?? '';
$timestamp = $data['timestamp'] ?? date('Y-m-d H:i:s');

if (!$table || !$id || !$step || !$status) {
    send_response(false, null, 'Missing required fields: table, id, step, status');
}

// Validate table name
if (!in_array($table, $ALLOWED_TABLES)) {
    send_response(false, null, 'Invalid table name');
}

// Validate step name
if (!in_array($step, $ALLOWED_STEPS)) {
    send_response(false, null, 'Invalid step name');
}

// Validate status
if (!in_array($status, $ALLOWED_STATUSES)) {
    send_response(false, null, 'Invalid status');
}

// Validate ID is numeric
if (!is_numeric($id)) {
    send_response(false, null, 'Invalid ID');
}

try {
    // Connect to database
    $dsn = "mysql:host={$DB_HOST};port={$DB_PORT};dbname={$DB_NAME};charset=utf8mb4";
    $pdo = new PDO($dsn, $DB_USER, $DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false
    ]);
    
    // Get current steps JSON
    $stmt = $pdo->prepare("SELECT steps FROM `{$table}` WHERE id = ?");
    $stmt->execute([$id]);
    $row = $stmt->fetch();
    
    if (!$row) {
        send_response(false, null, "Job ID {$id} not found in table {$table}");
    }
    
    // Parse existing steps or create new array
    $steps = [];
    if ($row['steps']) {
        $steps = json_decode($row['steps'], true);
        if (!is_array($steps)) {
            $steps = [];
        }
    }
    
    // Update the specific step
    $steps[$step] = [
        'status' => $status,
        'timestamp' => $timestamp
    ];
    
    // Add message if provided
    if ($message) {
        $steps[$step]['message'] = $message;
    }
    
    // Save back to database
    $steps_json = json_encode($steps);
    $update_stmt = $pdo->prepare("UPDATE `{$table}` SET steps = ?, updated_at = NOW() WHERE id = ?");
    $update_stmt->execute([$steps_json, $id]);
    
    // Also update the overall job status if all steps are done
    $all_done = true;
    $has_error = false;
    foreach ($ALLOWED_STEPS as $s) {
        if (isset($steps[$s])) {
            if ($steps[$s]['status'] === 'error') {
                $has_error = true;
            }
            if ($steps[$s]['status'] !== 'done') {
                $all_done = false;
            }
        } else {
            $all_done = false;
        }
    }
    
    // Update overall job status
    $new_status = null;
    if ($has_error) {
        $new_status = 'error';
    } elseif ($all_done) {
        $new_status = 'done';
    } elseif ($status === 'running') {
        $new_status = 'running';
    }
    
    if ($new_status) {
        $status_stmt = $pdo->prepare("UPDATE `{$table}` SET status = ? WHERE id = ?");
        $status_stmt->execute([$new_status, $id]);
    }
    
    // Return success
    send_response(true, [
        'id' => (int)$id,
        'table' => $table,
        'step' => $step,
        'status' => $status,
        'steps' => $steps,
        'overall_status' => $new_status
    ]);
    
} catch (PDOException $e) {
    log_error("Database error: " . $e->getMessage());
    send_response(false, null, 'Database error: ' . $e->getMessage());
} catch (Exception $e) {
    log_error("Error: " . $e->getMessage());
    send_response(false, null, 'Error: ' . $e->getMessage());
}
