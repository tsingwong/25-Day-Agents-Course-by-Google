# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A2A Extensions: Secure Passport Extension

This module implements the Secure Passport Extension for the A2A protocol.
The extension provides a "Sidecar" pattern for attaching custom authentication
and context data to A2A messages without breaking backward compatibility.

Key Concepts:
- CallerContext: Contains identity and state information from the calling agent
- A2AMessage: Standard A2A message with extension support
- Sidecar Pattern: Attach optional data that receivers can use or ignore
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import hashlib
import hmac
import json
from datetime import datetime, timezone


# Extension namespace - follows A2A extension URI convention
SECURE_PASSPORT_EXTENSION_URI = "a2a://extensions/secure-passport/v1"


@dataclass
class CallerContext:
    """
    CallerContext represents the identity and state of the calling agent.

    This is the "passport" that an agent can voluntarily share with another agent.
    It contains:
    - client_id: A URI identifying the calling agent (e.g., "a2a://travel-orchestrator.com")
    - state: A flexible dict for custom enterprise data (tier, billing codes, permissions, etc.)
    - signature: A cryptographic signature for verification
    - timestamp: When this context was created (for freshness validation)

    The receiving agent can use this information for:
    - Access control decisions
    - Billing/chargeback
    - Audit logging
    - Personalized responses based on tier/permissions
    """
    client_id: str
    state: dict = field(default_factory=dict)
    signature: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_verified(self) -> bool:
        """
        Check if the passport signature is valid.

        In a real implementation, this would:
        1. Fetch the public key from the client_id URI
        2. Verify the signature against the payload
        3. Check timestamp for freshness (prevent replay attacks)

        For this demo, we use a simple signature check.
        """
        if not self.signature:
            return False

        # Demo verification: check if signature matches expected pattern
        # In production, use asymmetric cryptography (RSA/ECDSA)
        expected_signature = self._compute_demo_signature()
        return hmac.compare_digest(self.signature, expected_signature)

    def _compute_demo_signature(self) -> str:
        """Compute a demo signature for verification."""
        # In production, this would be signed with a private key
        payload = f"{self.client_id}:{json.dumps(self.state, sort_keys=True)}"
        return hashlib.sha256(payload.encode()).hexdigest()[:32]

    def sign(self, secret_key: str = "demo-secret") -> "CallerContext":
        """
        Sign the passport with a secret key (demo implementation).

        In production:
        - Use the agent's private key
        - Include timestamp in signature
        - Use a proper JWT or similar standard
        """
        payload = f"{self.client_id}:{json.dumps(self.state, sort_keys=True)}"
        self.signature = hashlib.sha256(payload.encode()).hexdigest()[:32]
        return self

    def to_dict(self) -> dict:
        """Serialize to dictionary for transmission."""
        return {
            "client_id": self.client_id,
            "state": self.state,
            "signature": self.signature,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CallerContext":
        """Deserialize from dictionary."""
        return cls(
            client_id=data.get("client_id", ""),
            state=data.get("state", {}),
            signature=data.get("signature", ""),
            timestamp=data.get("timestamp", "")
        )


@dataclass
class A2AMessage:
    """
    A2AMessage represents a standard A2A protocol message.

    The A2A protocol uses JSON-RPC 2.0 format. This class provides
    a simplified representation with extension support.

    Key fields:
    - type: Message type (task, result, error, etc.)
    - content: The actual message payload
    - metadata: Standard A2A metadata (correlation IDs, etc.)
    - extensions: Dict of extension URIs to extension data (the "Sidecar")

    The extensions field is the key to A2A's extensibility:
    - It's optional - agents can ignore extensions they don't understand
    - It's namespaced by URI - prevents conflicts between extensions
    - It's type-safe when using helper functions like add_secure_passport()
    """
    type: str
    content: Any
    metadata: dict = field(default_factory=dict)
    extensions: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to A2A JSON-RPC format."""
        return {
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
            "extensions": self.extensions
        }

    @classmethod
    def from_dict(cls, data: dict) -> "A2AMessage":
        """Deserialize from A2A JSON-RPC format."""
        return cls(
            type=data.get("type", ""),
            content=data.get("content"),
            metadata=data.get("metadata", {}),
            extensions=data.get("extensions", {})
        )


def add_secure_passport(message: A2AMessage, passport: CallerContext) -> A2AMessage:
    """
    Add a Secure Passport to an A2A message.

    This is how the SENDER attaches context to outgoing messages.
    The passport is stored in the message's extensions under the
    secure-passport namespace URI.

    Args:
        message: The A2A message to augment
        passport: The CallerContext to attach

    Returns:
        The same message (modified in place) for chaining

    Example:
        >>> passport = CallerContext(
        ...     client_id="a2a://my-agent.com",
        ...     state={"tier": "Premium"}
        ... ).sign()
        >>> message = A2AMessage(type="task", content="Do something")
        >>> add_secure_passport(message, passport)
    """
    message.extensions[SECURE_PASSPORT_EXTENSION_URI] = passport.to_dict()
    return message


def get_secure_passport(message: A2AMessage) -> Optional[CallerContext]:
    """
    Extract a Secure Passport from an A2A message.

    This is how the RECEIVER inspects the context from incoming messages.
    Returns None if no passport is present - this is the "non-breaking
    fall-back behavior" that makes extensions backward compatible.

    Args:
        message: The A2A message to inspect

    Returns:
        CallerContext if present, None otherwise

    Example:
        >>> passport = get_secure_passport(message)
        >>> if passport and passport.is_verified:
        ...     print(f"Request from: {passport.client_id}")
        ... else:
        ...     print("Standard processing (no auth)")
    """
    ext_data = message.extensions.get(SECURE_PASSPORT_EXTENSION_URI)
    if ext_data is None:
        return None
    return CallerContext.from_dict(ext_data)


def has_secure_passport(message: A2AMessage) -> bool:
    """Check if a message has a Secure Passport extension."""
    return SECURE_PASSPORT_EXTENSION_URI in message.extensions


# ============================================================================
# Additional Extension Helpers
# ============================================================================

@dataclass
class ExtensionInfo:
    """Metadata about a registered extension."""
    uri: str
    name: str
    version: str
    description: str


def list_extensions(message: A2AMessage) -> list[str]:
    """List all extension URIs present in a message."""
    return list(message.extensions.keys())


def get_extension_data(message: A2AMessage, extension_uri: str) -> Optional[dict]:
    """Get raw extension data by URI."""
    return message.extensions.get(extension_uri)


# ============================================================================
# Demo: Run this module directly to see the extension in action
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("A2A Extensions Demo: Secure Passport")
    print("=" * 60)

    # 1. THE SENDER: Create and attach a passport
    print("\n1. SENDER: Creating secure passport...")

    passport = CallerContext(
        client_id="a2a://travel-orchestrator.example.com",
        state={
            "tier": "Platinum",
            "billing_code": "US-123",
            "permissions": ["book_flights", "book_hotels"],
            "user_id": "user_42"
        }
    ).sign()

    print(f"   Client ID: {passport.client_id}")
    print(f"   State: {passport.state}")
    print(f"   Signature: {passport.signature}")
    print(f"   Verified: {passport.is_verified}")

    # Create a message and stamp it with the passport
    message = A2AMessage(
        type="task",
        content={
            "action": "book_flight",
            "params": {
                "from": "SFO",
                "to": "JFK",
                "date": "2025-01-15"
            }
        },
        metadata={"correlation_id": "req-12345"}
    )

    add_secure_passport(message, passport)
    print("\n   Message extensions:")
    print(f"   {list_extensions(message)}")

    # 2. TRANSMISSION: Message is sent over the network (JSON serialization)
    print("\n2. TRANSMISSION: Message as JSON...")
    wire_format = json.dumps(message.to_dict(), indent=2)
    print(f"   {wire_format[:200]}...")

    # 3. THE RECEIVER: Extract and verify the passport
    print("\n3. RECEIVER: Inspecting incoming message...")

    # Simulate receiving the message
    received_message = A2AMessage.from_dict(json.loads(wire_format))
    received_passport = get_secure_passport(received_message)

    if received_passport and received_passport.is_verified:
        print(f"   Verified request from: {received_passport.client_id}")
        print(f"   Customer tier: {received_passport.state.get('tier')}")
        print(f"   Permissions: {received_passport.state.get('permissions')}")

        # Make authorization decisions based on passport
        if "book_flights" in received_passport.state.get("permissions", []):
            print("   Authorization: GRANTED for flight booking")
    else:
        print("   Standard processing (no verified passport)")

    # 4. BACKWARD COMPATIBILITY: Message without passport
    print("\n4. BACKWARD COMPATIBILITY: Message without passport...")

    plain_message = A2AMessage(
        type="task",
        content="Simple request"
    )

    plain_passport = get_secure_passport(plain_message)
    if plain_passport:
        print("   Found passport (unexpected)")
    else:
        print("   No passport found - falling back to standard processing")
        print("   This is the non-breaking fall-back behavior!")

    print("\n" + "=" * 60)
    print("Demo complete! The Sidecar pattern allows optional context")
    print("sharing without breaking agents that don't support it.")
    print("=" * 60)
