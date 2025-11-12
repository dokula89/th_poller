# API Endpoints Required for Step-by-Step Workflow

## Overview
The new step-by-step workflow requires several API endpoints to track and execute individual steps. Here's what needs to be created on the server.

## 1. Step Status API
**File**: `queue_step_api.php`
**URL**: `https://api.trustyhousing.com/manual_upload/queue_step_api.php`

### Purpose
Track the status of individual steps for each job.

### Method: POST
**Request Payload**:
```json
{
  "table": "queue_websites",
  "id": 123,
  "step": "capture_html",
  "status": "running",
  "message": "Optional message or error",
  "timestamp": "2025-10-30 12:34:56"
}
```

### Functionality
1. Update the `steps` JSON field in the job record
2. Store step status as: `pending`, `running`, `done`, or `error`
3. Store timestamp and optional message
4. Return success/error response

### Database Schema Addition
Add a `steps` column to queue tables:
```sql
ALTER TABLE `queue_websites` 
ADD COLUMN `steps` JSON DEFAULT NULL;

ALTER TABLE `listing_networks` 
ADD COLUMN `steps` JSON DEFAULT NULL;
```

### Example Update Logic (PHP)
```php
<?php
// Get current steps
$stmt = $pdo->prepare("SELECT steps FROM `{$table}` WHERE id = ?");
$stmt->execute([$id]);
$current_steps = $stmt->fetchColumn();

// Parse existing steps or create new
$steps = $current_steps ? json_decode($current_steps, true) : [];

// Update the specific step
$steps[$step] = [
    'status' => $status,
    'message' => $message,
    'timestamp' => $timestamp
];

// Save back to database
$stmt = $pdo->prepare("UPDATE `{$table}` SET steps = ? WHERE id = ?");
$stmt->execute([json_encode($steps), $id]);

echo json_encode(['ok' => true]);
?>
```

## 2. Process HTML with OpenAI
**File**: `process_html_with_openai.php`
**URL**: `https://api.trustyhousing.com/manual_upload/process_html_with_openai.php`

### Purpose
Extract structured listing data from HTML using OpenAI.

### Method: POST
**Request Payload**:
```json
{
  "html": "<html>...</html>",
  "job_id": 123,
  "url": "https://example.com/listing"
}
```

### Response
```json
{
  "ok": true,
  "data": {
    "title": "2 Bedroom Apartment",
    "rent": 1500,
    "bedrooms": 2,
    "bathrooms": 1,
    "sqft": 850,
    "description": "...",
    "amenities": ["parking", "laundry"],
    "images": ["url1", "url2"]
  }
}
```

### Implementation Notes
- Send HTML to OpenAI API with structured prompt
- Request JSON output with specific fields
- Validate and clean the response
- Handle API errors gracefully

## 3. Insert Listing
**File**: `insert_listing.php`
**URL**: `https://api.trustyhousing.com/manual_upload/insert_listing.php`

### Purpose
Insert extracted listing data into the `apartment_listings` table.

### Method: POST
**Request Payload**:
```json
{
  "data": {
    "title": "2 Bedroom Apartment",
    "rent": 1500,
    "bedrooms": 2,
    "bathrooms": 1,
    "sqft": 850,
    "description": "..."
  },
  "job_id": 123
}
```

### Response
```json
{
  "ok": true,
  "listing_id": 456
}
```

### Implementation Notes
- Insert into `apartment_listings` table
- Return the auto-increment `listing_id`
- Update the queue job with `listing_id` reference
- Handle duplicates appropriately

## 4. Rename Images
**File**: `rename_images.php`
**URL**: `https://api.trustyhousing.com/manual_upload/rename_images.php`

### Purpose
Rename uploaded images to include the apartment_listings ID.

### Method: POST
**Request Payload**:
```json
{
  "job_id": 123
}
```

### Response
```json
{
  "ok": true,
  "renamed": 5,
  "files": [
    "listing_456_1.jpg",
    "listing_456_2.jpg",
    "listing_456_3.jpg"
  ]
}
```

### Implementation Notes
1. Get `listing_id` from the job record
2. Find all images associated with the job
3. Rename from `job_123_*.jpg` to `listing_456_*.jpg`
4. Update image paths in the database
5. Return list of renamed files

### Example Logic (PHP)
```php
<?php
// Get listing_id from job
$stmt = $pdo->prepare("SELECT listing_id FROM queue_websites WHERE id = ?");
$stmt->execute([$job_id]);
$listing_id = $stmt->fetchColumn();

// Find images for this job
$image_dir = "/home/daniel/trustyhousing.com/app/public/img/";
$pattern = "job_{$job_id}_*.jpg";
$files = glob($image_dir . $pattern);

$renamed = [];
foreach ($files as $i => $file) {
    $new_name = "listing_{$listing_id}_" . ($i + 1) . ".jpg";
    $new_path = $image_dir . $new_name;
    rename($file, $new_path);
    $renamed[] = $new_name;
}

echo json_encode(['ok' => true, 'renamed' => count($renamed), 'files' => $renamed]);
?>
```

## 5. Enhanced Queue API (Update)
**File**: `queue_website_api.php` (modify existing)
**URL**: `https://api.trustyhousing.com/manual_upload/queue_website_api.php`

### Addition Needed
Include the `steps` field in the response:

```json
{
  "ok": true,
  "data": [
    {
      "id": 123,
      "link": "https://example.com",
      "status": "queued",
      "steps": {
        "capture_html": {"status": "done", "timestamp": "2025-10-30 12:34:56"},
        "create_json": {"status": "running", "timestamp": "2025-10-30 12:35:12"},
        "extract_images": {"status": "pending"},
        "upload_images": {"status": "pending"},
        "process_db": {"status": "pending"},
        "rename_images": {"status": "pending"}
      }
    }
  ]
}
```

## Testing the APIs

### Test Step Status API
```bash
curl -X POST https://api.trustyhousing.com/manual_upload/queue_step_api.php \
  -H "Content-Type: application/json" \
  -d '{
    "table": "queue_websites",
    "id": 1,
    "step": "capture_html",
    "status": "running",
    "timestamp": "2025-10-30 12:34:56"
  }'
```

### Test OpenAI Processing
```bash
curl -X POST https://api.trustyhousing.com/manual_upload/process_html_with_openai.php \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<html>test</html>",
    "job_id": 1,
    "url": "https://example.com"
  }'
```

### Test Insert Listing
```bash
curl -X POST https://api.trustyhousing.com/manual_upload/insert_listing.php \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"title": "Test Apartment", "rent": 1000},
    "job_id": 1
  }'
```

### Test Rename Images
```bash
curl -X POST https://api.trustyhousing.com/manual_upload/rename_images.php \
  -H "Content-Type: application/json" \
  -d '{"job_id": 1}'
```

## Database Schema Changes

```sql
-- Add steps column to all queue tables
ALTER TABLE `queue_websites` ADD COLUMN `steps` JSON DEFAULT NULL;
ALTER TABLE `listing_networks` ADD COLUMN `steps` JSON DEFAULT NULL;
ALTER TABLE `parcel` ADD COLUMN `steps` JSON DEFAULT NULL;
ALTER TABLE `code` ADD COLUMN `steps` JSON DEFAULT NULL;
ALTER TABLE `911` ADD COLUMN `steps` JSON DEFAULT NULL;

-- Add listing_id reference to queue tables
ALTER TABLE `queue_websites` ADD COLUMN `listing_id` INT DEFAULT NULL;
ALTER TABLE `listing_networks` ADD COLUMN `listing_id` INT DEFAULT NULL;
```

## Priority Order for Implementation

1. **queue_step_api.php** - Critical for tracking step status
2. **Modify queue_website_api.php** - Include steps in response
3. **process_html_with_openai.php** - Core AI processing
4. **insert_listing.php** - Database insertion
5. **rename_images.php** - Final cleanup step

## Notes
- All APIs should use proper authentication/authorization
- Include error handling and logging
- Return consistent JSON response format
- Use transactions where appropriate
- Add rate limiting for OpenAI calls
