Hosting your static and media files on AWS S3 with Django is a common practice to offload file storage from your local server. Here’s a detailed step-by-step guide to setting up and configuring AWS S3 for Django static and media files.

### Prerequisites:

-   An AWS account (sign up at [AWS](https://aws.amazon.com) if you don’t have one).
-   The `ecom_prj` Django project ready.
-   The `boto3` and `django-storages` libraries installed.

---

### Step 1: Set Up an S3 Bucket on AWS

1. **Log in to AWS Console:**

    - Go to [AWS Management Console](https://aws.amazon.com/console/), log in, and navigate to the **S3** service.

2. **Create a New S3 Bucket:**

    - Click **Create Bucket**.
    - Enter a unique bucket name (e.g., `ecom-prj-static`).
    - Choose the AWS region closest to your server location.
    - **Disable block all public access** and configure specific access if you plan to make your files publicly accessible (for static files). Otherwise, leave public access blocked for private media files.
    - Leave other settings as default and click **Create Bucket**.

3. **Configure Bucket Permissions:**

    - Once the bucket is created, go to the **Permissions** tab.
    - Scroll down to **Bucket Policy** and set up a bucket policy that allows public access for static files (optional but required for public access). You can use the following example policy:
        ```json
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::ecom-prj-static/*"
                }
            ]
        }
        ```
        Replace `ecom-prj-static` with your actual bucket name.

4. **Enable CORS (Optional):**
    - If you need your static files accessible from other domains, configure **CORS** (Cross-Origin Resource Sharing):
        - Under the **Permissions** tab, go to **CORS Configuration** and add this:
        ```json
        [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET"],
                "AllowedOrigins": ["*"],
                "ExposeHeaders": []
            }
        ]
        ```

---

### Step 2: Create an IAM User with S3 Access

1. **Navigate to IAM (Identity and Access Management):**
    - In the AWS Console, search for **IAM** and click on it.
2. **Create a New IAM User:**

    - Click **Users** > **Add Users**.
    - Enter a username (e.g., `ecom-prj-user`).
    - For **Access Type**, select **Programmatic Access** (this will give you an Access Key ID and Secret Access Key for your Django app).
    - Click **Next: Permissions**.

3. **Assign Permissions to the User:**

    - Select **Attach existing policies directly**.
    - Search for the **AmazonS3FullAccess** policy and select it.
    - Click **Next: Tags**, add any tags if necessary, and click **Next: Review**, then **Create User**.

4. **Save the Access Key and Secret Key:**
    - After the user is created, you will be provided with an **Access Key ID** and **Secret Access Key**. Save these somewhere secure as you will need them to configure Django.

---

### Step 3: Install Required Django Packages

1. **Install `boto3` and `django-storages`:**
   These libraries are necessary for integrating Django with AWS S3.

    - Run the following command in your Django project’s virtual environment:

    ```bash
    pip install boto3 django-storages
    ```

2. **Add `storages` to Installed Apps:**
   In your `settings.py`, add `'storages'` to the `INSTALLED_APPS`:
    ```python
    INSTALLED_APPS = [
        # other apps
        'storages',
    ]
    ```

---

### Step 4: Configure Django Settings for S3

You need to update your `settings.py` to configure S3 for storing static and media files.

1. **Configure AWS Settings:**
   Add the following S3 settings to your `settings.py`:

    ```python
    # AWS S3 Settings
    AWS_ACCESS_KEY_ID = '<your-access-key-id>'
    AWS_SECRET_ACCESS_KEY = '<your-secret-access-key>'
    AWS_STORAGE_BUCKET_NAME = 'ecom-prj-static'
    AWS_S3_REGION_NAME = 'us-east-1'  # Replace with your region
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

    # Static Files Configuration
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

    # Media Files Configuration
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    ```

2. **Update `STATIC_ROOT` and `MEDIA_ROOT`:**
   You can leave these as they are in case you want to collect files locally for development but set `STATIC_URL` and `MEDIA_URL` to point to S3 for production:
    ```python
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Used for collectstatic locally
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Used to upload media locally
    ```

---

### Step 5: Update Storage Classes (Optional)

You can set custom S3 storage backends for both static and media files by creating custom storage classes in your project.

1. **Create a `storages.py` file** in the project’s main app (same level as `settings.py`):

    ```python
    from storages.backends.s3boto3 import S3Boto3Storage

    class StaticStorage(S3Boto3Storage):
        location = 'static'
        default_acl = 'public-read'

    class MediaStorage(S3Boto3Storage):
        location = 'media'
        file_overwrite = False
    ```

2. **Update `settings.py` to use these custom storage backends:**
    ```python
    STATICFILES_STORAGE = 'ecom_prj.storages.StaticStorage'
    DEFAULT_FILE_STORAGE = 'ecom_prj.storages.MediaStorage'
    ```

This way, your static files will be stored in an S3 bucket folder named `static` and media files in `media`.

---

### Step 6: Run Collectstatic

Now that S3 is configured, you need to collect all static files from your Django project and upload them to the S3 bucket.

1. **Run the collectstatic command:**

    ```bash
    python manage.py collectstatic
    ```

    This command will gather all static files (CSS, JS, images, etc.) from your apps and place them in the `static/` folder inside the S3 bucket.

2. **Check Your S3 Bucket:**
   Go to the AWS S3 console and navigate to your bucket. You should see the files under the `static/` folder.

---

### Step 7: Verify Media File Uploads

1. **Test Media Upload:**
   If your Django project allows file uploads (e.g., user profile pictures), try uploading a file through the Django admin or any form.
2. **Check Your S3 Bucket:**
   After uploading, go to the S3 bucket, and check the `media/` folder to ensure the uploaded file is stored there.

---

### Step 8: Make S3 Bucket Private (Optional)

If you want to ensure that only authorized users can access the media files (such as user-uploaded content), you can make the media files private by configuring AWS and Django to serve private content.

1. **Make Bucket Private:**
   Go to the S3 console, select the bucket, and update the bucket policy to remove public access to the media folder.

2. **Use Signed URLs for Private Files:**
   In `storages.py`, update the `MediaStorage` class to use signed URLs:

    ```python
    class MediaStorage(S3Boto3Storage):
        location = 'media'
        file_overwrite = False
        default_acl = 'private'
        querystring_auth = True
    ```

    This way, media files will require a signed URL (with temporary access) for users to download or view.

---

### Step 9: Test Your Application

1. **Run Your Django Application:**
   Start your Django server locally or on your production environment.

    ```bash
    python manage.py runserver
    ```

2. **Verify Static Files:**
   Ensure that all static files (CSS, JS, etc.) are being served from the S3 bucket when you load the web application in your browser.

3. **Verify Media Files:**
   Test any file uploads to make sure media files are being uploaded to S3 and that they are accessible (if public) or secured with signed URLs (if private).

---

You have now successfully configured your Django project to store static and media files on AWS S3! This setup improves performance and offloads file management from your application server, making it more scalable and cost-effective, send am email to desphixs@gmail.com for more help.
