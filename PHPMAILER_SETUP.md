# PHPMailer Installation Guide for XAMPP

## Step 1: Install Composer (if not already installed)

1. Download Composer from: https://getcomposer.org/download/
2. Run the installer and select your PHP from XAMPP (usually `C:\xampp\php\php.exe`)
3. Complete the installation

## Step 2: Install PHPMailer via Composer

Open Command Prompt or PowerShell and navigate to your htdocs folder:

```bash
cd C:\xampp\htdocs
```

Then install PHPMailer:

```bash
composer require phpmailer/phpmailer
```

This will create a `vendor` folder with PHPMailer and autoloader.

## Step 3: Copy Files to XAMPP htdocs

Copy these files to `C:\xampp\htdocs\`:

1. `send_email_api.php` - The email API endpoint
2. `vendor/` folder (created by Composer)

## Step 4: Test the Installation

1. Start Apache in XAMPP Control Panel
2. Open browser and go to: `http://localhost/send_email_api.php`
3. You should see a JSON response: `{"success":false,"error":"Only POST requests are allowed"}`

This confirms the API is working (it's just blocking GET requests).

## Step 5: Database Setup (Already Done)

The following tables have been created:
- `email_send_log` - Tracks all email sends
- `sms_send_log` - Tracks all SMS sends
- Newsletter table updated with:
  - `contact_type` (email/sms/both)
  - `last_email_sent`
  - `last_sms_sent`

## Step 6: Testing Email Sending

From the Python application:
1. Click the "Mailer" button
2. Click the play button (▶️ Send) next to any email subscriber
3. Check the email send log table to see the result

## Troubleshooting

### If emails don't send:

1. **Check Gmail Settings:**
   - The account `neatlylisted@gmail.com` needs "App Password" enabled
   - Go to Google Account → Security → 2-Step Verification → App Passwords
   - Generate a new app password if `itkx gxns ceam mcak` doesn't work

2. **Check PHP Error Log:**
   - Look in `C:\xampp\apache\logs\error.log`

3. **Test PHPMailer directly:**
   Create a test file `test_email.php`:
   ```php
   <?php
   require 'vendor/autoload.php';
   use PHPMailer\PHPMailer\PHPMailer;
   
   $mail = new PHPMailer(true);
   try {
       $mail->isSMTP();
       $mail->Host = 'smtp.gmail.com';
       $mail->SMTPAuth = true;
       $mail->Username = 'neatlylisted@gmail.com';
       $mail->Password = 'itkx gxns ceam mcak';
       $mail->SMTPSecure = 'ssl';
       $mail->Port = 465;
       
       $mail->setFrom('admin@seattlelisted.com', 'Test');
       $mail->addAddress('your-test-email@gmail.com');
       $mail->Subject = 'Test Email';
       $mail->Body = 'This is a test';
       
       $mail->send();
       echo 'Email sent successfully!';
   } catch (Exception $e) {
       echo "Error: {$mail->ErrorInfo}";
   }
   ?>
   ```

4. **Check Firewall:**
   - Make sure port 465 (SMTP SSL) is not blocked
   - Windows Firewall may need to allow PHP to make outbound connections

## Features Implemented

✅ Email sending to individual subscribers
✅ Bulk email sending to all subscribers
✅ Email send logging (tracks success/failure)
✅ Last email sent timestamp per subscriber
✅ Contact type tracking (email/sms/both)
✅ Error handling and status messages
✅ Confirmation dialogs before sending
✅ Background thread for bulk sends (non-blocking UI)

## Next Steps for SMS

To implement SMS sending, you'll need:
1. SMS provider API (Twilio, AWS SNS, etc.)
2. Create `send_sms_api.php` similar to email API
3. Update Python code to call SMS API
4. Add SMS credentials to the PHP file
