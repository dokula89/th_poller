<?php
/**
 * Price Changes Email (Last 24 Hours)
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
    
    // Query price changes
    $pcSql = "
        SELECT
            pc.id AS pc_id,
            pc.apartment_listings_id AS listing_id,
            pc.new_price AS new_price,
            pc.time AS change_time,
            al.title AS listing_title,
            al.full_address AS full_address,
            al.price AS current_price,
            al.bedrooms, al.bathrooms, al.sqft,
            al.img_urls,
            al.`Building_Name` AS al_building_name,
            al.network AS source_network,
            (
                SELECT pc0.new_price
                FROM apartment_listings_price_changes pc0
                WHERE pc0.apartment_listings_id = pc.apartment_listings_id
                ORDER BY pc0.time ASC
                LIMIT 1
            ) AS original_price,
            (
                SELECT pc2.new_price
                FROM apartment_listings_price_changes pc2
                WHERE pc2.apartment_listings_id = pc.apartment_listings_id
                  AND pc2.time < pc.time
                ORDER BY pc2.time DESC
                LIMIT 1
            ) AS prev_price
        FROM apartment_listings_price_changes pc
        JOIN apartment_listings al ON al.id = pc.apartment_listings_id
        WHERE pc.time >= (NOW() - INTERVAL ? HOUR)
        ORDER BY pc.time DESC
        LIMIT ?
    ";
    
    $priceChanges = [];
    if ($stmt2 = $conn->prepare($pcSql)) {
        $stmt2->bind_param("ii", $hoursWindow, $limit);
        $stmt2->execute();
        $res = $stmt2->get_result();
        while ($row = $res->fetch_assoc()) {
            $priceChanges[] = $row;
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
    
    $html .= "<h1 style='text-align:center;margin:0'>SeattleListed Price Changes</h1>";
    $html .= "<p style='text-align:center;margin:4px 0 16px'><span class='pill'>Last 24 Hours</span></p>";
    $html .= "<table><thead><tr><th>Image</th><th>Property</th><th>Price</th></tr></thead><tbody>";
    
    if (empty($priceChanges)) {
        $html .= "<tr><td colspan='3'>No price changes in the last 24 hours.</td></tr>";
    } else {
        foreach ($priceChanges as $pc) {
            $imgHtml = '';
            if (!empty($pc['img_urls'])) {
                $arr = explode('|', $pc['img_urls']);
                $first = trim($arr[0]);
                if ($first !== '') {
                    $imgHtml = '<img src="' . h($first) . '" alt="Listing" style="max-width:100px; max-height:100px;">';
                }
            }
            
            $propName = trim((string)($pc['al_building_name'] ?? ''));
            if ($propName === '') {
                $propName = trim((string)($pc['full_address'] ?? ''));
            }
            
            $addrLine = '';
            if (!empty($pc['full_address'])) {
                $addrEnc = rawurlencode($pc['full_address']);
                $mapUrl = 'https://www.google.com/maps/search/?api=1&query=' . $addrEnc;
                $addrLine = "<br><small><a href=\"" . h($mapUrl) . "\">" . h($pc['full_address']) . "</a></small>";
            }
            
            $listingId = (int)$pc['listing_id'];
            $idHtml = ' <span class="pill">ID #' . h($listingId) . '</span>';
            $propertyCol = h($propName) . $idHtml . $addrLine;
            
            $curr = null;
            if (isset($pc['current_price']) && is_numeric($pc['current_price'])) {
                $curr = (float)$pc['current_price'];
            } elseif (isset($pc['new_price']) && is_numeric($pc['new_price'])) {
                $curr = (float)$pc['new_price'];
            }
            
            $baseline = null;
            if (isset($pc['original_price']) && is_numeric($pc['original_price'])) {
                $baseline = (float)$pc['original_price'];
            } elseif (isset($pc['prev_price']) && is_numeric($pc['prev_price'])) {
                $baseline = (float)$pc['prev_price'];
            }
            
            if ($curr !== null) {
                $deltaHtml = '';
                if ($baseline !== null) {
                    $delta = $curr - $baseline;
                    if (abs($delta) >= 1) {
                        $sign = $delta > 0 ? '+' : '−';
                        $deltaAbs = number_format(abs($delta));
                        $deltaColor = $delta > 0 ? '#2e7d32' : '#c62828';
                        $deltaHtml = " <span style=\"color: {$deltaColor}; font-weight:600;\">{$sign}$${deltaAbs}</span>";
                    }
                }
                $priceCol = "<b>$" . h(number_format($curr)) . "</b>" . $deltaHtml;
            } else {
                $priceCol = "—";
            }
            
            $html .= '<tr><td>' . $imgHtml . '</td><td>' . $propertyCol . '</td><td>' . $priceCol . '</td></tr>';
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
        $mail->Subject = 'SeattleListed - Price Changes (Last 24h)';
        $mail->Body = $html;
        
        $mail->send();
        
        // Log the send
        $log_stmt = $conn->prepare("INSERT INTO email_send_log (subscriber_id, email, subject, sent_at, status) VALUES (?, ?, ?, NOW(), 'sent')");
        $subject = 'Price Changes (Last 24h)';
        $log_stmt->bind_param("iss", $subscriber_id, $email, $subject);
        $log_stmt->execute();
        
        // Update subscriber
        $update_stmt = $conn->prepare("UPDATE newsletter SET last_email_sent = NOW() WHERE id = ?");
        $update_stmt->bind_param("i", $subscriber_id);
        $update_stmt->execute();
        
        echo json_encode(['success' => true, 'message' => 'Price changes email sent successfully', 'count' => count($priceChanges)]);
        
    } catch (Exception $e) {
        echo json_encode(['success' => false, 'error' => "Mailer Error: {$mail->ErrorInfo}"]);
    }
    
} else {
    echo json_encode(['success' => false, 'error' => 'Only POST requests are allowed']);
}

$conn->close();
?>
