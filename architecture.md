# Report Architecture

## 1. Related Repositories

- **Missive conversation sidebar**
  - https://github.com/PublicDataWorks/txt-outlier-convo-sidebar
- **Missive broadcast sidebar**
  - https://github.com/PublicDataWorks/txt-outlier-frontend
- **Broadcast backend**
  - https://github.com/PublicDataWorks/txt-outlier-backend
- **Lookup backend**
  - https://github.com/PublicDataWorks/txt-outlier-lookups

## 2. Config Variables Description

### Environment Variables

- `SUPABASE_SERVICE_ROLE_KEY`: A secret key used for Supabase service role access, granting full database access.
- `JWT_SECRET`: A secret key used to sign and verify JSON Web Tokens for authentication.
- `HMAC_SECRET`: A secret key used for HMAC (Hash-based Message Authentication Code) operations.
- `DATABASE_URL`: The connection string for your database.
- `OPENAI_API_KEY`: Your API key for accessing OpenAI services.
- `PHONE_NUMBER`: A phone number, possibly for SMS notifications or verification.
- `SUPABASE_ID`: The unique identifier for your Supabase project.
- `API_KEY`: A secret key from Supbase
- `MISSIVE_SECRET`: A secret key for authenticating with the Missive API.
- `MISSIVE_ORGANIZATION`: The organization identifier for your Missive account.
- `MISSIVE_WEEKLY_REPORT_CONVERSATION_ID`: The ID of a specific conversation in Missive for weekly reports.
- `SFTP_HOST`: The hostname or IP address of the SFTP server(Detroit rental property data)
- `SFTP_USERNAME`: The username for authenticating with the SFTP server.
- `SFTP_PASSWORD`: The password for authenticating with the SFTP server.
- `BACKEND_URL`: The URL of your backend server.
- `SUMMARY_CONVO_SIDEBAR_ADDRESS`: Possibly an address or endpoint for a conversation summary sidebar feature.

## 3. Deploy Steps: https://docs.google.com/document/d/1eiyfUTgwDB1aTH9ofmQ65IHEmW6GeEPOKOsnSqoUuhc/edit

## 4. Migration: https://github.com/PublicDataWorks/txt-outlier-import/tree/main/supabase/functions/user-actions/drizzle

## Important Note on Environment Variables
🔐 **Security Notice**: 
All environment variables and sensitive configuration data mentioned in this document are securely stored in 1Password. For access to these variables, please refer to the project's vault in 1Password. Never share these credentials openly or store them in unsecured locations.
