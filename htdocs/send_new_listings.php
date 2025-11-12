<?php
/**
 * New Listings Email (Last 24 Hours)
 * Adapted for local use with send_email_api.php
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Database connection
$servername = "localhost";
$username = "local_uzr";
$password = "fuck";
$database = "offta";

$conn = new mysqli($servername, $username, $password, $database);

if ($conn->connect_error) {
    die(json_encode(['success' => false, 'error' => 'Database connection failed: ' . $conn->connect_error]));
}

// Load Composer's autoloader
require 'vendor/autoload.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

// For escaping HTML
function h($s) { return htmlspecialchars((string)$s ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }

// Handle POST request
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    
    $subscriber_id = $input['subscriber_id'] ?? null;
    $hoursWindow = 24;
    $limit = 500;
    
    if (!$subscriber_id) {
        echo json_encode(['success' => false, 'error' => 'subscriber_id is required']);
        exit;
    }
    
    // Get subscriber info
    $stmt = $conn->prepare("SELECT id, name, method, method_type FROM newsletter WHERE id = ?");
    $stmt->bind_param("i", $subscriber_id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if (!($subscriber = $result->fetch_assoc())) {
        echo json_encode(['success' => false, 'error' => 'Subscriber not found']);
        exit;
    }
    
    $email = $subscriber['method'];
    
    // Query new listings
    $nlSql = "
        SELECT
            al.id AS listing_id,
            al.title AS listing_title,
            al.full_address,
            al.bedrooms, al.bathrooms, al.sqft,
            al.price, al.img_urls,
            al.`Building_Name` AS al_building_name,
            al.time_created,
            al.network AS source_network
        FROM apartment_listings al
        WHERE al.time_created >= (NOW() - INTERVAL ? HOUR)
        ORDER BY al.time_created DESC
        LIMIT ?
    ";
    
    $newListings = [];
    if ($stmt2 = $conn->prepare($nlSql)) {
        $stmt2->bind_param("ii", $hoursWindow, $limit);
        $stmt2->execute();
        $res = $stmt2->get_result();
        while ($row = $res->fetch_assoc()) {
            $newListings[] = $row;
        }
        $stmt2->close();
    }
    
    // Build HTML
    $html = '<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: Arial, sans-serif; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { border: 1px solid #000; padding: 8px; text-align: center; vertical-align: middle; }
    th { background-color: #000; color: #fff; }
    small { color: #555; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; background:#eef2ff; color:#3949ab; font-size:12px; border:1px solid #c5cae9; }
  </style>
</head>
<body>';
    
    $html .= "<h1 style='text-align:center;margin:0'>SeattleListed New Listings</h1>";
    $html .= "<p style='text-align:center;margin:4px 0 16px'><span class='pill'>Last 24 Hours</span></p>";
    $html .= "<table><thead><tr><th>Image</th><th>Property</th><th>Price</th></tr></thead><tbody>";
    
    if (empty($newListings)) {
        $html .= "<tr><td colspan='3'>No new listings in the last 24 hours.</td></tr>";
    } else {
        foreach ($newListings as $nl) {
            $imgHtml = '';
            if (!empty($nl['img_urls'])) {
                $arr = explode('|', $nl['img_urls']);
                $first = trim($arr[0]);
                if ($first !== '') {
                    $imgHtml = '<img src="' . h($first) . '" alt="Listing" style="max-width:100px; max-height:100px;">';
                }
            }
            
            $propName = trim((string)($nl['al_building_name'] ?? ''));
            if ($propName === '') {
                $propName = trim((string)($nl['full_address'] ?? ''));
            }
            
            $addrLine = '';
            if (!empty($nl['full_address'])) {
                $addrEnc = rawurlencode($nl['full_address']);
                $mapUrl = 'https://www.google.com/maps/search/?api=1&query=' . $addrEnc;
                $addrLine = "<br><small><a href=\"" . h($mapUrl) . "\">" . h($nl['full_address']) . "</a></small>";
            }
            
            $listingId = (int)$nl['listing_id'];
            $idHtml = ' <span class="pill">ID #' . h($listingId) . '</span>';
            $propertyCol = h($propName) . $idHtml . $addrLine;
            
            $priceVal = ($nl['price'] !== null && $nl['price'] !== '') ? '$' . number_format((float)$nl['price']) : '—';
            
            $html .= '<tr><td>' . $imgHtml . '</td><td>' . $propertyCol . '</td><td>' . h($priceVal) . '</td></tr>';
        }
    }
    
    $html .= '</tbody></table></body></html>';
    
    // Send email using PHPMailer
    $mail = new PHPMailer(true);
    
    try {
        $mail->SMTPDebug = 0;
        $mail->isSMTP();
        $mail->Host = 'smtp.gmail.com';
        $mail->SMTPAuth = true;
        $mail->Username = 'neatlylisted@gmail.com';
        $mail->Password = 'itkx gxns ceam mcak';
        $mail->SMTPSecure = PHPMailer::ENCRYPTION_SMTPS;
        $mail->Port = 465;
        
        $mail->setFrom('admin@seattlelisted.com', 'SeattleListed.com');
        $mail->addAddress($email);
        
        $mail->isHTML(true);
        $mail->Subject = 'SeattleListed - New Listings (Last 24h)';
        $mail->Body = $html;
        
        $mail->send();
        
        // Log the send
        $log_stmt = $conn->prepare("INSERT INTO email_send_log (subscriber_id, email, subject, sent_at, status) VALUES (?, ?, ?, NOW(), 'sent')");
        $subject = 'New Listings (Last 24h)';
        $log_stmt->bind_param("iss", $subscriber_id, $email, $subject);
        $log_stmt->execute();
        
        // Update subscriber
        $update_stmt = $conn->prepare("UPDATE newsletter SET last_email_sent = NOW() WHERE id = ?");
        $update_stmt->bind_param("i", $subscriber_id);
        $update_stmt->execute();
        
        echo json_encode(['success' => true, 'message' => 'New listings email sent successfully', 'count' => count($newListings)]);
        
    } catch (Exception $e) {
        echo json_encode(['success' => false, 'error' => "Mailer Error: {$mail->ErrorInfo}"]);
    }
    
} else {
    echo json_encode(['success' => false, 'error' => 'Only POST requests are allowed']);
}

$conn->close();
?>
