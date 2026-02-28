# Site Report PDF — Google Cloud Function

Generates a professional PDF from annotated site photos.

## Deploy

1. Install the gcloud CLI: https://cloud.google.com/sdk/docs/install
2. Authenticate: `gcloud auth login`
3. Set your project: `gcloud config set project YOUR_PROJECT_ID`
4. Deploy:

```bash
cd cloud-function

gcloud functions deploy generate_site_report \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point generate_site_report \
  --memory 512MB \
  --timeout 120s \
  --region us-central1
```

5. Copy the deployed URL and update `CLOUD_FUNCTION_URL` in `crew.html`.

## Optional: Add Company Logo

Place a `logo.png` file in the `assets/` directory before deploying. The cover page will display it automatically. If no logo is present, the cover page still renders with text only.

## Local Testing

```bash
pip install -r requirements.txt
functions-framework --target generate_site_report --port 8080
```

Then update `CLOUD_FUNCTION_URL` in crew.html to `http://localhost:8080` for testing.

## API

**POST** `/` (multipart/form-data)

- `metadata` (string): JSON with `{ address, inspector, date, photos: [{ note }] }`
- `photos` (files): JPEG images with annotations already composited

**Response**: `application/pdf` binary
