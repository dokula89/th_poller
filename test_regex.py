import re

text = "INSERT INTO `queue_websites` (`id`, `link`, `the_css`, `capture_mode`, `status`, `priority`, `attempts`, `last_error`, `source_table`, `source_id`, `output_json_path`, `created_at`, `updated_at`, `processed_at`, `hash_key`, `run_interval_minutes`, `steps`, `listing_id`)"

print("BEFORE:", text)
result = re.sub(r"(`processed_at`),\s*`hash_key`", r"\1", text)
print("AFTER:", result)
print("MATCH:", "hash_key" in result)
