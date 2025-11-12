<?php
/**
 * Email sending API endpoint using PHPMailer
 * Receives POST requests to send emails to newsletter subscribers
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Database connection
$servername = "localhost";
$username = "seattlelisted_usr";
$password = "T@5z6^pl}";
$database = "offta";

$conn = new mysqli($servername, $username, $password, $database);

if ($conn->connect_error) {
    die(json_encode(['success' => false, 'error' => 'Database connection failed: ' . $conn->connect_error]));
}

// Load Composer's autoloader
require 'vendor/autoload.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

function send_email($email, $subject, $message, $conn) {
    $mail = new PHPMailer(true);
    
    try {
        // Server settings
        $mail->SMTPDebug = 0; // Disable debug output
        $mail->isSMTP();
        $mail->Host = 'smtp.gmail.com';
        $mail->SMTPAuth = true;
        $mail->Username = 'neatlylisted@gmail.com';
        $mail->Password = 'itkx gxns ceam mcak';
        $mail->SMTPSecure = 'ssl';
        $mail->Port = 465;
        
        // Recipients
        $mail->setFrom('admin@seattlelisted.com', 'SeattleListed.com Admin');
        $mail->addAddress($email);
        
        // Content
        $mail->isHTML(true);
        $mail->Subject = $subject;
        $mail->Body = $message;
        
        $mail->send();
        return ['success' => true, 'message' => 'Email sent successfully'];
        
    } catch (Exception $e) {
        return ['success' => false, 'error' => "Mailer Error: {$mail->ErrorInfo}"];
    }
}

// Handle POST request
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    
    $action = $input['action'] ?? '';
    $subscriber_id = $input['subscriber_id'] ?? null;
    $subject = $input['subject'] ?? 'SeattleListed Newsletter';
    $message = $input['message'] ?? '';
    
    if (empty($message)) {
        echo json_encode(['success' => false, 'error' => 'Message content is required']);
        exit;
    }
    
    $results = [];
    
    if ($action === 'send_to_one' && $subscriber_id) {
        // Send to single subscriber
        $stmt = $conn->prepare("SELECT id, name, method, method_type FROM newsletter WHERE id = ?");
        $stmt->bind_param("i", $subscriber_id);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($subscriber = $result->fetch_assoc()) {
            if ($subscriber['method_type'] === 'email' || strpos($subscriber['method'], '@') !== false) {
                $email_result = send_email($subscriber['method'], $subject, $message, $conn);
                
                if ($email_result['success']) {
                    // Log the send
                    $log_stmt = $conn->prepare("INSERT INTO email_send_log (subscriber_id, email, subject, sent_at, status) VALUES (?, ?, ?, NOW(), 'sent')");
                    $log_stmt->bind_param("iss", $subscriber['id'], $subscriber['method'], $subject);
                    $log_stmt->execute();
                    
                    // Update subscriber with last_email_sent
                    $update_stmt = $conn->prepare("UPDATE newsletter SET last_email_sent = NOW() WHERE id = ?");
                    $update_stmt->bind_param("i", $subscriber['id']);
                    $update_stmt->execute();
                }
                
                $results[] = [
                    'subscriber_id' => $subscriber['id'],
                    'name' => $subscriber['name'],
                    'email' => $subscriber['method'],
                    'result' => $email_result
                ];
            } else {
                $results[] = [
                    'subscriber_id' => $subscriber['id'],
                    'name' => $subscriber['name'],
                    'result' => ['success' => false, 'error' => 'Not an email subscriber']
                ];
            }
        }
        
        // Return response for single subscriber
        if (!empty($results)) {
            $first_result = $results[0];
            echo json_encode([
                'success' => $first_result['result']['success'],
                'subscriber_id' => $first_result['subscriber_id'],
                'name' => $first_result['name'],
                'error' => $first_result['result']['error'] ?? null,
                'message' => $first_result['result']['message'] ?? null
            ]);
        } else {
            echo json_encode(['success' => false, 'error' => 'Subscriber not found']);
        }
        exit;
        
    } elseif ($action === 'send_to_all') {
        // Send to all email subscribers
        $result = $conn->query("SELECT id, name, method, method_type FROM newsletter WHERE method_type = 'email' OR method LIKE '%@%'");
        
        $sent_count = 0;
        $failed_count = 0;
        
        while ($subscriber = $result->fetch_assoc()) {
            $email_result = send_email($subscriber['method'], $subject, $message, $conn);
            
            if ($email_result['success']) {
                $sent_count++;
                
                // Log the send
                $log_stmt = $conn->prepare("INSERT INTO email_send_log (subscriber_id, email, subject, sent_at, status) VALUES (?, ?, ?, NOW(), 'sent')");
                $log_stmt->bind_param("iss", $subscriber['id'], $subscriber['method'], $subject);
                $log_stmt->execute();
                
                // Update subscriber
                $update_stmt = $conn->prepare("UPDATE newsletter SET last_email_sent = NOW() WHERE id = ?");
                $update_stmt->bind_param("i", $subscriber['id']);
                $update_stmt->execute();
            } else {
                $failed_count++;
                
                // Log the failure
                $log_stmt = $conn->prepare("INSERT INTO email_send_log (subscriber_id, email, subject, sent_at, status, error_message) VALUES (?, ?, ?, NOW(), 'failed', ?)");
                $log_stmt->bind_param("isss", $subscriber['id'], $subscriber['method'], $subject, $email_result['error']);
                $log_stmt->execute();
            }
            
            $results[] = [
                'subscriber_id' => $subscriber['id'],
                'name' => $subscriber['name'],
                'email' => $subscriber['method'],
                'result' => $email_result
            ];
            
            // Small delay to avoid rate limiting
            usleep(100000); // 0.1 second
        }
        
        echo json_encode([
            'success' => true,
            'sent_count' => $sent_count,
            'failed_count' => $failed_count,
            'total' => $sent_count + $failed_count,
            'details' => $results
        ]);
        exit;
    }
    
    echo json_encode([
        'success' => true,
        'results' => $results
    ]);
    
} else {
    echo json_encode(['success' => false, 'error' => 'Only POST requests are allowed']);
}

$conn->close();
?>
