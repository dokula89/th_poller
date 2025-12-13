<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

// Database connection (external Linode server)
$servername = "172.104.206.182";
$username = "seattlelisted_usr";
$password = "T@5z6^pl}";
$dbname = "offta";

try {
    $conn = new PDO("mysql:host=$servername;dbname=$dbname", $username, $password);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    // Get metro_name parameter
    $metro_name = isset($_GET['metro_name']) ? trim($_GET['metro_name']) : '';
    
    if (empty($metro_name)) {
        echo json_encode([
            'success' => false,
            'message' => 'metro_name parameter is required'
        ]);
        exit;
    }
    
    // Query major_metros table
    $stmt = $conn->prepare("SELECT id, metro_name, county_name, lat, lng, parcel_link, parcel_x_y, state FROM major_metros WHERE metro_name = :metro_name LIMIT 1");
    $stmt->bindParam(':metro_name', $metro_name);
    $stmt->execute();
    
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if ($result) {
        echo json_encode([
            'success' => true,
            'data' => $result
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'message' => 'Metro not found'
        ]);
    }
    
} catch(PDOException $e) {
    echo json_encode([
        'success' => false,
        'message' => 'Database error: ' . $e->getMessage()
    ]);
}

$conn = null;
?>
