"""
Authentication Service - OAuth2 and credential management
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import logging
import secrets
import uuid
from pydantic import BaseModel, Field
import jwt
import aiohttp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)

class AuthType(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    CUSTOM = "custom"

class OAuth2Flow(str, Enum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"

class CredentialStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"

class OAuth2Config(BaseModel):
    """OAuth2 configuration"""
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    refresh_url: Optional[str] = None
    scopes: List[str] = []
    redirect_uri: str
    pkce: bool = False

class CredentialDefinition(BaseModel):
    """Definition of stored credentials"""
    credential_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    connector_name: str
    auth_type: AuthType
    config: Dict[str, Any] = {}
    credentials: Dict[str, Any] = {}  # Encrypted sensitive data
    status: CredentialStatus = CredentialStatus.ACTIVE
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

class OAuth2State(BaseModel):
    """OAuth2 state for authorization flow"""
    state_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    connector_name: str
    config: OAuth2Config
    code_verifier: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(minutes=10))

class TokenResponse(BaseModel):
    """OAuth2 token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None

class CredentialEncryption:
    """Encryption for sensitive credential data"""
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self.salt = b"integration_platform_salt"  # In production, use proper salt management
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        
        # Simple XOR encryption - in production, use proper encryption like AES
        data_bytes = data.encode()
        encrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key[i % len(key)])
        
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted = bytearray()
        
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ key[i % len(key)])
        
        return decrypted.decode()

class OAuth2Manager:
    """OAuth2 flow manager"""
    
    def __init__(self, encryption: CredentialEncryption):
        self.encryption = encryption
        self.states: Dict[str, OAuth2State] = {}
    
    def initiate_flow(
        self,
        user_id: str,
        connector_name: str,
        config: OAuth2Config,
        flow: OAuth2Flow = OAuth2Flow.AUTHORIZATION_CODE
    ) -> Dict[str, Any]:
        """Initiate OAuth2 flow"""
        state_id = str(uuid.uuid4())
        state = secrets.token_urlsafe(32)
        
        # Create state record
        oauth_state = OAuth2State(
            state_id=state_id,
            user_id=user_id,
            connector_name=connector_name,
            config=config
        )
        
        # Handle PKCE if required
        if config.pkce:
            oauth_state.code_verifier = secrets.token_urlsafe(64)
            code_challenge = self._generate_code_challenge(oauth_state.code_verifier)
        else:
            code_challenge = None
        
        self.states[state_id] = oauth_state
        
        # Build authorization URL
        auth_params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": " ".join(config.scopes)
        }
        
        if code_challenge:
            auth_params["code_challenge"] = code_challenge
            auth_params["code_challenge_method"] = "S256"
        
        auth_url = f"{config.authorization_url}?{self._build_query_string(auth_params)}"
        
        return {
            "authorization_url": auth_url,
            "state_id": state_id,
            "state": state
        }
    
    async def exchange_code_for_token(
        self,
        state_id: str,
        code: str,
        state: str
    ) -> Optional[TokenResponse]:
        """Exchange authorization code for access token"""
        oauth_state = self.states.get(state_id)
        if not oauth_state:
            return None
        
        # Verify state
        if not self._verify_state(oauth_state, state):
            return None
        
        # Exchange code for token
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oauth_state.config.redirect_uri,
            "client_id": oauth_state.config.client_id,
            "client_secret": oauth_state.config.client_secret
        }
        
        if oauth_state.code_verifier:
            token_data["code_verifier"] = oauth_state.code_verifier
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    oauth_state.config.token_url,
                    data=token_data
                ) as response:
                    if response.status == 200:
                        token_json = await response.json()
                        return TokenResponse(**token_json)
                    else:
                        logger.error(f"Token exchange failed: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Token exchange error: {str(e)}")
            return None
        
        finally:
            # Clean up state
            del self.states[state_id]
    
    async def refresh_token(
        self,
        refresh_token: str,
        config: OAuth2Config
    ) -> Optional[TokenResponse]:
        """Refresh access token"""
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.client_id,
            "client_secret": config.client_secret
        }
        
        token_url = config.refresh_url or config.token_url
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=token_data) as response:
                    if response.status == 200:
                        token_json = await response.json()
                        return TokenResponse(**token_json)
                    else:
                        logger.error(f"Token refresh failed: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return None
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code challenge"""
        import hashlib
        import base64
        
        challenge = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(challenge).decode().rstrip("=")
    
    def _verify_state(self, oauth_state: OAuth2State, state: str) -> bool:
        """Verify OAuth2 state"""
        # In production, verify against stored state
        return True
    
    def _build_query_string(self, params: Dict[str, str]) -> str:
        """Build query string from parameters"""
        return "&".join(f"{k}={v}" for k, v in params.items())

class CredentialManager:
    """Manager for storing and retrieving credentials"""
    
    def __init__(self, encryption: CredentialEncryption):
        self.encryption = encryption
        self.credentials: Dict[str, CredentialDefinition] = {}
        self.user_credentials: Dict[str, List[str]] = {}  # user_id -> credential_ids
    
    def store_credential(self, credential: CredentialDefinition) -> str:
        """Store encrypted credentials"""
        # Encrypt sensitive data
        encrypted_credentials = {}
        for key, value in credential.credentials.items():
            if self._is_sensitive_field(key):
                encrypted_credentials[key] = self.encryption.encrypt(str(value))
            else:
                encrypted_credentials[key] = value
        
        credential.credentials = encrypted_credentials
        
        # Store credential
        self.credentials[credential.credential_id] = credential
        
        # Update user index
        if credential.user_id not in self.user_credentials:
            self.user_credentials[credential.user_id] = []
        self.user_credentials[credential.user_id].append(credential.credential_id)
        
        logger.info(f"Stored credential for user {credential.user_id}, connector {credential.connector_name}")
        return credential.credential_id
    
    def get_credential(self, credential_id: str, decrypt: bool = True) -> Optional[CredentialDefinition]:
        """Get credential by ID"""
        credential = self.credentials.get(credential_id)
        if not credential:
            return None
        
        if not decrypt:
            return credential
        
        # Decrypt sensitive data
        decrypted_credentials = {}
        for key, value in credential.credentials.items():
            if self._is_sensitive_field(key):
                try:
                    decrypted_credentials[key] = self.encryption.decrypt(value)
                except Exception as e:
                    logger.error(f"Failed to decrypt field {key}: {str(e)}")
                    decrypted_credentials[key] = value
            else:
                decrypted_credentials[key] = value
        
        # Create copy with decrypted data
        credential_copy = credential.copy()
        credential_copy.credentials = decrypted_credentials
        
        return credential_copy
    
    def get_user_credentials(
        self,
        user_id: str,
        connector_name: str = None
    ) -> List[CredentialDefinition]:
        """Get all credentials for a user"""
        credential_ids = self.user_credentials.get(user_id, [])
        credentials = []
        
        for credential_id in credential_ids:
            credential = self.get_credential(credential_id)
            if credential:
                if not connector_name or credential.connector_name == connector_name:
                    credentials.append(credential)
        
        return credentials
    
    def update_credential(self, credential_id: str, updates: Dict[str, Any]) -> bool:
        """Update credential"""
        credential = self.credentials.get(credential_id)
        if not credential:
            return False
        
        for key, value in updates.items():
            if hasattr(credential, key):
                setattr(credential, key, value)
        
        credential.updated_at = datetime.now()
        return True
    
    def revoke_credential(self, credential_id: str) -> bool:
        """Revoke a credential"""
        return self.update_credential(credential_id, {"status": CredentialStatus.REVOKED})
    
    def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential"""
        credential = self.credentials.get(credential_id)
        if not credential:
            return False
        
        # Remove from user index
        if credential.user_id in self.user_credentials:
            self.user_credentials[credential.user_id].remove(credential_id)
        
        # Delete credential
        del self.credentials[credential_id]
        return True
    
    def check_expiration(self) -> List[str]:
        """Check for expired credentials and return their IDs"""
        expired_ids = []
        now = datetime.now()
        
        for credential_id, credential in self.credentials.items():
            if (credential.expires_at and 
                credential.expires_at <= now and 
                credential.status == CredentialStatus.ACTIVE):
                credential.status = CredentialStatus.EXPIRED
                expired_ids.append(credential_id)
        
        return expired_ids
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field contains sensitive data"""
        sensitive_fields = [
            "password", "token", "secret", "key", "credential",
            "access_token", "refresh_token", "client_secret"
        ]
        return any(sensitive in field_name.lower() for sensitive in sensitive_fields)

class AuthenticationService:
    """Main authentication service"""
    
    def __init__(self, master_key: str):
        self.encryption = CredentialEncryption(master_key)
        self.oauth2_manager = OAuth2Manager(self.encryption)
        self.credential_manager = CredentialManager(self.encryption)
        self.jwt_secret = secrets.token_urlsafe(32)
    
    def initiate_oauth2_flow(
        self,
        user_id: str,
        connector_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Initiate OAuth2 authentication flow"""
        oauth_config = OAuth2Config(**config)
        return self.oauth2_manager.initiate_flow(user_id, connector_name, oauth_config)
    
    async def complete_oauth2_flow(
        self,
        state_id: str,
        code: str,
        state: str
    ) -> Optional[str]:
        """Complete OAuth2 flow and store credentials"""
        # Exchange code for token
        token_response = await self.oauth2_manager.exchange_code_for_token(
            state_id, code, state
        )
        
        if not token_response:
            return None
        
        # Get the OAuth state to retrieve user and connector info
        oauth_state = self.oauth2_manager.states.get(state_id)
        if not oauth_state:
            return None
        
        # Calculate expiration
        expires_at = None
        if token_response.expires_in:
            expires_at = datetime.now() + timedelta(seconds=token_response.expires_in)
        
        # Create credential
        credential = CredentialDefinition(
            user_id=oauth_state.user_id,
            connector_name=oauth_state.connector_name,
            auth_type=AuthType.OAUTH2,
            config=oauth_state.config.dict(),
            credentials={
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "scope": token_response.scope
            },
            expires_at=expires_at
        )
        
        # Store credential
        return self.credential_manager.store_credential(credential)
    
    async def refresh_credential(self, credential_id: str) -> bool:
        """Refresh an OAuth2 credential"""
        credential = self.credential_manager.get_credential(credential_id)
        if not credential or credential.auth_type != AuthType.OAUTH2:
            return False
        
        oauth_config = OAuth2Config(**credential.config)
        refresh_token = credential.credentials.get("refresh_token")
        
        if not refresh_token:
            return False
        
        # Refresh token
        token_response = await self.oauth2_manager.refresh_token(
            refresh_token, oauth_config
        )
        
        if not token_response:
            return False
        
        # Update credential with new token
        updates = {
            "credentials": {
                **credential.credentials,
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token or refresh_token,
                "token_type": token_response.token_type,
                "scope": token_response.scope
            }
        }
        
        if token_response.expires_in:
            updates["expires_at"] = datetime.now() + timedelta(seconds=token_response.expires_in)
        
        return self.credential_manager.update_credential(credential_id, updates)
    
    def store_api_key_credential(
        self,
        user_id: str,
        connector_name: str,
        api_key: str,
        additional_data: Dict[str, Any] = None
    ) -> str:
        """Store API key credential"""
        credential = CredentialDefinition(
            user_id=user_id,
            connector_name=connector_name,
            auth_type=AuthType.API_KEY,
            credentials={
                "api_key": api_key,
                **(additional_data or {})
            }
        )
        
        return self.credential_manager.store_credential(credential)
    
    def store_basic_auth_credential(
        self,
        user_id: str,
        connector_name: str,
        username: str,
        password: str
    ) -> str:
        """Store basic auth credential"""
        credential = CredentialDefinition(
            user_id=user_id,
            connector_name=connector_name,
            auth_type=AuthType.BASIC_AUTH,
            credentials={
                "username": username,
                "password": password
            }
        )
        
        return self.credential_manager.store_credential(credential)
    
    def get_credentials_for_connector(
        self,
        user_id: str,
        connector_name: str
    ) -> List[CredentialDefinition]:
        """Get all credentials for a user and connector"""
        return self.credential_manager.get_user_credentials(user_id, connector_name)
    
    def get_active_credential(
        self,
        user_id: str,
        connector_name: str
    ) -> Optional[CredentialDefinition]:
        """Get active credential for user and connector"""
        credentials = self.get_credentials_for_connector(user_id, connector_name)
        
        for credential in credentials:
            if credential.status == CredentialStatus.ACTIVE:
                # Check if expired
                if credential.expires_at and credential.expires_at <= datetime.now():
                    credential.status = CredentialStatus.EXPIRED
                    continue
                
                return credential
        
        return None
    
    def generate_jwt_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Generate JWT token for API authentication"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def verify_jwt_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return user_id"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload.get("user_id")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def auto_refresh_expired_credentials(self):
        """Automatically refresh expired OAuth2 credentials"""
        expired_ids = self.credential_manager.check_expiration()
        
        for credential_id in expired_ids:
            await self.refresh_credential(credential_id)
    
    def get_credential(self, user_id: str, connector_type: str) -> Optional[CredentialDefinition]:
        """Get stored credential for a user and connector type"""
        credential_id = f"{user_id}_{connector_type}"
        return self.credential_manager.get_credential(credential_id)

    def store_credential(self, user_id: str, connector_type: str, config: Dict[str, Any]) -> bool:
        """Store credential for a user and connector type"""
        credential_id = f"{user_id}_{connector_type}"
        
        # Create credential object
        credential = CredentialDefinition(
            credential_id=credential_id,
            user_id=user_id,
            connector_name=connector_type,
            auth_type=self._get_auth_type(connector_type),
            config=config,
            status=CredentialStatus.ACTIVE,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year expiry
        )
        
        return self.credential_manager.store_credential(credential)
    
    def _get_auth_type(self, connector_type: str) -> AuthType:
        """Get auth type for connector"""
        auth_type_mapping = {
            "slack": AuthType.OAUTH2,
            "http": AuthType.API_KEY,
            "gmail": AuthType.OAUTH2,
            "github": AuthType.API_KEY
        }
        return auth_type_mapping.get(connector_type, AuthType.API_KEY)

    def get_system_stats(self) -> Dict[str, Any]:
        """Get authentication system statistics"""
        credentials = list(self.credential_manager.credentials.values())
        
        return {
            "total_credentials": len(credentials),
            "credentials_by_type": {
                auth_type.value: len([c for c in credentials if c.auth_type == auth_type])
                for auth_type in AuthType
            },
            "credentials_by_status": {
                status.value: len([c for c in credentials if c.status == status])
                for status in CredentialStatus
            }
        }

# Global authentication service
auth_service = AuthenticationService(master_key="default_master_key_change_in_production")
