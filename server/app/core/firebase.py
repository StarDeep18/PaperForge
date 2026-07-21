import os
import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import get_settings
from app.core.logging import logger

def initialize_firebase():
    """
    Initialize the Firebase Admin SDK.
    Loads credentials from the configured certificates file path or falls back to Application Default Credentials.
    """
    if firebase_admin._apps:
        return
        
    settings = get_settings()
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH") or settings.firebase_credentials_path
    
    if cred_path and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK initialized successfully using certificate from {cred_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin using certificate path {cred_path}: {e}")
            raise e
    else:
        try:
            # Fallback to default credentials or environment settings
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized using Application Default Credentials (or environment default)")
        except Exception as e:
            # Non-blocking logger warning because during test mode or mock-token mode, credentials might not exist.
            logger.warning(
                "Firebase Admin SDK could not initialize using default configuration. "
                "Real token validation will fail, but mock tokens will work. Error: %s", e
            )

def verify_firebase_token(token: str) -> dict:
    """
    Verify the given Firebase ID Token.
    Supports a mock token format for automated test isolation:
    Format: mock-token-{status}-{uid}-{display_name}-{email}
    """
    if token and token.startswith("mock-token-"):
        parts = token.split("-")
        if len(parts) >= 4:
            # e.g., mock-token-valid-uid123-User-user@domain.com
            status = parts[2]
            if status == "valid":
                uid = parts[3]
                display_name = parts[4] if len(parts) > 4 else "Mock User"
                email = parts[5] if len(parts) > 5 else f"{uid}@example.com"
                return {
                    "uid": uid,
                    "name": display_name,
                    "email": email,
                    "firebase": {"sign_in_provider": "password"}
                }
            elif status == "expired":
                raise ValueError("Token has expired")
            elif status == "invalid":
                raise ValueError("Token signature is invalid")
        raise ValueError("Malformed mock token payload")
        
    try:
        initialize_firebase()
        return auth.verify_id_token(token)
    except Exception as e:
        logger.error(f"Firebase token verification error: {e}")
        raise ValueError(f"Firebase verification failed: {str(e)}")
