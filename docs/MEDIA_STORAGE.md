# Media Storage — tiqani_v3

## Overview

Media files (profile images, documents, proof files) can be stored either on the **local filesystem** (development default) or on **any S3-compatible object storage** provider.

Supported providers:

- **AWS S3** — standard
- **Cloudflare R2** — S3-compatible
- **DigitalOcean Spaces** — S3-compatible
- **Backblaze B2** — S3-compatible mode
- **MinIO** — local/staging self-hosted

---

## Configuration

All settings are controlled via environment variables. Copy `.env.example` to `.env`.

### Local Mode (default for development)

```
USE_S3_MEDIA=False
```

Files are stored at `MEDIA_ROOT` (default: `media/`) and served via Django's `MEDIA_URL`.

### S3 Mode (production)

```
USE_S3_MEDIA=True
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_STORAGE_BUCKET_NAME=your-bucket-name
S3_REGION_NAME=us-east-1
S3_ENDPOINT_URL=                          # Optional: for S3-compatible providers
S3_CUSTOM_DOMAIN=                         # Optional: custom CDN domain
S3_QUERYSTRING_EXPIRE=900                 # Signed URL expiry in seconds (15 min)
```

#### Cloudflare R2 Example

```
USE_S3_MEDIA=True
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_STORAGE_BUCKET_NAME=tiqani-media
S3_ACCESS_KEY_ID=<r2-access-key-id>
S3_SECRET_ACCESS_KEY=<r2-secret-access-key>
S3_REGION_NAME=auto
S3_ADDRESSING_STYLE=path
```

#### DigitalOcean Spaces Example

```
USE_S3_MEDIA=True
S3_ENDPOINT_URL=https://<region>.digitaloceanspaces.com
S3_STORAGE_BUCKET_NAME=tiqani-media
S3_ACCESS_KEY_ID=<spaces-key>
S3_SECRET_ACCESS_KEY=<spaces-secret>
S3_REGION_NAME=<region>
S3_CUSTOM_DOMAIN=tiqani-media.<region>.digitaloceanspaces.com
```

#### MinIO Local Example

```
USE_S3_MEDIA=True
S3_ENDPOINT_URL=http://minio:9000
S3_STORAGE_BUCKET_NAME=tiqani-media
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_REGION_NAME=us-east-1
S3_ADDRESSING_STYLE=path
```

---

## Private Media by Default

All uploaded files are **private** by default. They are **not** publicly accessible.

- `default_acl`: `private`
- `querystring_auth`: `True`
- `querystring_expire`: 900 seconds (15 minutes)

Accessing a file requires a short-lived signed URL. The URL expires after the configured time and cannot be used after expiry.

### How Signed URLs Work

1. A user requests access to a file through an authorized API endpoint.
2. The backend generates a temporary signed URL using the S3 credentials.
3. The URL is valid for `S3_QUERYSTRING_EXPIRE` seconds (default: 900 / 15 min).
4. The client downloads the file directly from the storage provider.
5. After expiry, a new signed URL must be generated.

---

## File Validation

All uploads are validated server-side:

| Field Type | Allowed Extensions | Max Size |
|---|---|---|
| Profile image | `.jpg`, `.jpeg`, `.png`, `.webp` | 2 MB |
| Category icon | `.jpg`, `.jpeg`, `.png`, `.webp` | 1 MB |
| Documents (ID, guarantee) | `.pdf`, `.jpg`, `.jpeg`, `.png` | 10 MB |
| Proof files (recharge, receipt) | `.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp` | 5 MB |

### Blocked File Types

The following are **always rejected** regardless of extension matching:

- Executables: `.exe`, `.bat`, `.cmd`, `.sh`, `.ps1`, `.vbs`
- Archives: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`
- Video: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
- Scripts: `.js`, `.ts`, `.py`, `.html`, `.svg`
- Installers: `.dmg`, `.app`, `.iso`

### Additional Security

- Files without extensions are rejected.
- Content-type checking is done when available.
- Double extensions (e.g., `image.jpg.exe`) are caught by the extension check.
- File overwrite is disabled — each upload creates a new unique path.

---

## Upload Limits

| Setting | Default | Description |
|---|---|---|
| `MAX_PROFILE_IMAGE_SIZE_MB` | 2 MB | Profile/avatar images |
| `MAX_CATEGORY_ICON_SIZE_MB` | 1 MB | Category icons |
| `MAX_DOCUMENT_SIZE_MB` | 10 MB | ID docs, guarantee documents |
| `MAX_PROOF_FILE_SIZE_MB` | 5 MB | Receipts, proof files |

---

## File Path Organization

Files are organized by purpose using `upload_to` paths:

```
media/
  users/
    profiles/       # Profile images
  technicians/
    portfolio/      # Technician portfolio images
    documents/      # ID documents
  categories/
    icons/          # Category icons
  dealerships/
    guarantees/     # Guarantee documents
    recharges/
      proofs/       # Recharge proof files
    cashouts/
      proofs/       # Cashout proof files
```

---

## Cost-Control Checklist

- [x] File overwrite disabled (`S3_FILE_OVERWRITE=False`)
- [x] Hard max upload sizes enforced
- [x] No video upload support
- [x] No archive upload support
- [x] Private ACL by default
- [x] Short signed URL expiry (15 min default)
- [x] Local dev defaults to local media (no S3 costs)
- [ ] Lifecycle policy configured in S3 bucket (see below)
- [ ] Access logs enabled for cost monitoring
- [ ] Bucket size alerts configured

### Lifecycle Policy Recommendations

Configure a bucket lifecycle policy to move old files to cheaper storage:

1. **Current files (0-90 days)**: Standard storage
2. **Warm (90-365 days)**: Transition to Infrequent Access (IA) / One Zone-IA
3. **Cold (365+ days)**: Transition to Glacier / Deep Archive
4. **Expired files (> 1095 days)**: Consider deletion based on legal requirements

Example AWS S3 lifecycle rule (JSON):

```json
{
  "Rules": [
    {
      "Id": "tier-to-ia",
      "Status": "Enabled",
      "Filter": {"Prefix": "media/"},
      "Transitions": [
        {"Days": 90, "StorageClass": "STANDARD_IA"},
        {"Days": 365, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 1095}
    }
  ]
}
```

### Access Logs

Enable S3 server access logs to monitor storage usage and detect unauthorized access attempts. Configure logs to be stored in a separate auditing bucket.

---

## Upload Size Hard Limits

The backend enforces hard limits. The client-side `MAX_UPLOAD_SIZE` in JavaScript should match these values:

- Profile image: 2 MB (2,097,152 bytes)
- Category icon: 1 MB (1,048,576 bytes)
- Document: 10 MB (10,485,760 bytes)
- Proof file: 5 MB (5,242,880 bytes)

Files exceeding these limits are rejected with a clear error message before any storage operation.

---

## Security Warnings

1. **Never commit `.env` files** with real S3 credentials.
2. **Never use public-read ACL** — always use private with signed URLs.
3. **Never serve media files directly from Django in production** — use nginx/CDN.
4. **Never allow uploads without extension validation** — RCE risk.
5. **Never allow executable files** — even if renamed, content-type checks help.

---

## Migration from Local to S3

1. Set `USE_S3_MEDIA=True` in production environment.
2. Run `python manage.py check_media_storage` to verify settings.
3. Optionally run `python manage.py check_media_storage --test-upload` to verify S3 connectivity.
4. Existing local files will not be migrated automatically — use `aws s3 sync` or Django management command.
5. Update nginx/CDN configuration to serve signed URLs or proxy to S3.
6. Verify a few file URLs work correctly.
7. Disable local media serving in production settings.

### Migrate Existing Files to S3

```bash
# Using AWS CLI (or compatible)
aws s3 sync media/ s3://your-bucket/media/ --endpoint-url <optional>
```

---

## Management Command

```bash
python manage.py check_media_storage
```

Shows:
- Current media mode (local or S3)
- Upload limits
- S3 configuration warnings (missing vars, public ACL, long expiry)
- S3 connectivity test (with `--test-upload` flag)

---

## Testing S3 Settings

```bash
# Test with S3 disabled (default)
python manage.py check_media_storage

# Test with S3 enabled (set env vars first)
export USE_S3_MEDIA=True
export S3_STORAGE_BUCKET_NAME=test-bucket
export S3_ACCESS_KEY_ID=test-key
export S3_SECRET_ACCESS_KEY=test-secret
export S3_REGION_NAME=us-east-1
python manage.py check_media_storage
python manage.py check_media_storage --test-upload
```
