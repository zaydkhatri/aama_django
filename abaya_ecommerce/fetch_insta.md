# Instagram Integration Setup

This document provides step-by-step instructions for setting up Instagram API integration with your Abaya Ecommerce website.

## Prerequisites

1. A Facebook Developer account
2. An Instagram Business or Creator account
3. A Facebook Page connected to your Instagram account

## Steps to Set Up Instagram Graph API Access

### 1. Create a Facebook App

1. Go to [Facebook for Developers](https://developers.facebook.com/)
2. Click on "My Apps" and then "Create App"
3. Select "Business" as the app type
4. Fill in the required information and create your app

### 2. Set Up Instagram Basic Display API

1. From your app dashboard, add the "Instagram Basic Display" product
2. Go to the Basic Display section and configure your app:
   - Add your app's Privacy Policy URL
   - Add your website's URL to the "Deauthorize Callback URL" and "Data Deletion Request URL"

### 3. Create an Instagram Test User

1. Go to the "Roles" > "Test Users" section in your app
2. Add yourself or the Instagram account you want to use as a test user
3. Follow the instructions to connect your Instagram account

### 4. Generate an Access Token

1. Go to the Instagram Basic Display > User Token Generator
2. Click on "Generate Token" for your Test User
3. Log in with your Instagram credentials and authorize the app
4. Copy the generated access token

### 5. Set Up Environment Variables

Add the following to your `.env` file:

```
INSTAGRAM_ACCESS_TOKEN=your_access_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_account_id_here
```

## Important Notes

- The Basic Display API access token expires after 60 days. You'll need to implement token refresh logic for production.
- For a proper production setup, use the Instagram Graph API with a long-lived token.
- Make sure your Instagram account is set to Business or Creator account type.

## Additional Resources

- [Instagram Basic Display API Documentation](https://developers.facebook.com/docs/instagram-basic-display-api/)
- [Instagram Graph API Documentation](https://developers.facebook.com/docs/instagram-api/)
- [Facebook Token Debugging Tool](https://developers.facebook.com/tools/debug/accesstoken/)

## Troubleshooting

If no videos appear on your site, check the following:

1. Verify your access token is valid using the Facebook Token Debugging Tool
2. Make sure you have posted videos on your Instagram account
3. Check the developer console for any JavaScript errors
4. Look at your server logs for any API errors

For more support, refer to the [Facebook Developer Support](https://developers.facebook.com/support/).