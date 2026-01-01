# ruff: noqa
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
Day 20: A2A Extensions - Secure Auth Agent

This agent demonstrates how to use A2A Extensions (Secure Passport)
to handle authenticated requests with custom enterprise context.

The agent provides different service levels based on the caller's passport:
- Platinum tier: Full access with priority processing
- Gold tier: Standard access
- No passport: Basic public access only
"""

import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth

# Import our Secure Passport extension
from secure_passport_ext import (
    CallerContext,
    A2AMessage,
    add_secure_passport,
    get_secure_passport,
    has_secure_passport,
)

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


# ============================================================================
# Tier-based Service Functions
# ============================================================================

def get_flight_deals(query: str) -> str:
    """Get flight deals. Results vary by customer tier.

    Args:
        query: Search query including destination and dates.

    Returns:
        Flight deal information based on access tier.
    """
    # In a real implementation, this would check the A2A request context
    # For demo, we simulate tier-based responses
    basic_deals = """
    Public Flight Deals:
    - NYC to LA: $299 (Economy)
    - Chicago to Miami: $249 (Economy)
    """

    premium_deals = """
    Platinum Member Exclusive Deals:
    - NYC to LA: $199 (Economy) or $599 (Business Class - 40% off!)
    - Chicago to Miami: $149 (Economy) or $449 (Business Class)
    - Tokyo to Paris: $899 (Business Class - Members Only!)
    - Private Jet Charter: 20% discount for Platinum members
    """

    # Simulate checking passport (in real A2A, this comes from request context)
    if "platinum" in query.lower():
        return premium_deals
    return basic_deals


def book_flight(
    origin: str,
    destination: str,
    date: str,
    passenger_name: str,
    cabin_class: str = "economy"
) -> str:
    """Book a flight. Requires appropriate authorization level.

    Args:
        origin: Departure airport code (e.g., 'SFO')
        destination: Arrival airport code (e.g., 'JFK')
        date: Travel date in YYYY-MM-DD format
        passenger_name: Name of the passenger
        cabin_class: Cabin class (economy, business, first)

    Returns:
        Booking confirmation or error message.
    """
    # Validate inputs
    if not all([origin, destination, date, passenger_name]):
        return "Error: Missing required booking information."

    # Simulate booking
    confirmation_number = f"A2A-{hash(f'{origin}{destination}{date}') % 100000:05d}"

    return f"""
    Flight Booking Confirmed!
    =========================
    Confirmation: {confirmation_number}
    Route: {origin} -> {destination}
    Date: {date}
    Passenger: {passenger_name}
    Class: {cabin_class.title()}

    Status: CONFIRMED
    """


def get_loyalty_points(member_id: str) -> str:
    """Get loyalty points balance. Requires verified passport.

    Args:
        member_id: The member's loyalty program ID.

    Returns:
        Points balance and tier status.
    """
    # Simulate loyalty data
    return f"""
    Loyalty Program Status
    =====================
    Member ID: {member_id}
    Current Points: 125,000
    Tier: Platinum
    Miles to Maintain: 0 (Lifetime status)

    Recent Activity:
    - +5,000 pts: Flight SFO-JFK (Dec 15)
    - +2,500 pts: Hotel Partner Booking
    - +1,000 pts: Car Rental Partner
    """


def get_current_time(city: str) -> str:
    """Get current time for a city.

    Args:
        city: The city name.

    Returns:
        Current time in that city's timezone.
    """
    tz_map = {
        "san francisco": "America/Los_Angeles",
        "sf": "America/Los_Angeles",
        "new york": "America/New_York",
        "nyc": "America/New_York",
        "london": "Europe/London",
        "tokyo": "Asia/Tokyo",
        "paris": "Europe/Paris",
    }

    tz_identifier = tz_map.get(city.lower())
    if not tz_identifier:
        return f"Sorry, I don't have timezone information for {city}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time in {city} is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"


# ============================================================================
# A2A Extension Handler (Middleware Pattern)
# ============================================================================

class SecurePassportMiddleware:
    """
    Middleware to handle Secure Passport extension in A2A requests.

    This demonstrates how an agent can:
    1. Extract passport from incoming A2A messages
    2. Make authorization decisions based on passport data
    3. Customize responses based on caller context
    """

    def __init__(self):
        self.current_passport: Optional[CallerContext] = None

    def process_request(self, message: A2AMessage) -> dict:
        """
        Process an incoming A2A request and extract passport context.

        Returns authorization context for use in tool execution.
        """
        self.current_passport = get_secure_passport(message)

        if self.current_passport and self.current_passport.is_verified:
            return {
                "authorized": True,
                "client_id": self.current_passport.client_id,
                "tier": self.current_passport.state.get("tier", "Standard"),
                "permissions": self.current_passport.state.get("permissions", []),
                "billing_code": self.current_passport.state.get("billing_code"),
            }
        else:
            return {
                "authorized": False,
                "client_id": None,
                "tier": "Public",
                "permissions": ["search"],  # Public access only
                "billing_code": None,
            }

    def can_perform(self, action: str) -> bool:
        """Check if current caller can perform an action."""
        if not self.current_passport:
            # Public access - limited actions
            return action in ["search", "get_time"]

        permissions = self.current_passport.state.get("permissions", [])
        return action in permissions or "admin" in permissions


# Global middleware instance
passport_middleware = SecurePassportMiddleware()


# ============================================================================
# Agent Definition
# ============================================================================

AGENT_INSTRUCTION = """You are a Travel Assistant Agent with A2A Extension support.

You help users with:
1. Finding flight deals (get_flight_deals)
2. Booking flights (book_flight) - requires proper authorization
3. Checking loyalty points (get_loyalty_points) - requires verified identity
4. Getting current time in cities (get_current_time)

When handling requests:
- Always be helpful and provide accurate information
- If a user mentions "platinum" in their query, provide premium deals
- For booking requests, collect all required information before proceeding
- Explain any limitations based on access level

Security Note: This agent supports the Secure Passport A2A Extension.
Verified callers get enhanced access and personalized service.
"""

root_agent = Agent(
    name="secure_travel_agent",
    model=Gemini(
        model="gemini-2.0-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        get_flight_deals,
        book_flight,
        get_loyalty_points,
        get_current_time,
    ],
)

app = App(root_agent=root_agent, name="secure-auth-agent")


# ============================================================================
# Demo: Simulating A2A Communication with Extensions
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("A2A Extensions Demo: Secure Auth Agent")
    print("=" * 70)

    # Scenario 1: Platinum member request with verified passport
    print("\n--- Scenario 1: Platinum Member Request ---")

    platinum_passport = CallerContext(
        client_id="a2a://travel-orchestrator.example.com",
        state={
            "tier": "Platinum",
            "billing_code": "CORP-123",
            "permissions": ["search", "book_flights", "book_hotels", "loyalty_access"],
            "user_id": "user_platinum_42"
        }
    ).sign()

    platinum_request = A2AMessage(
        type="task",
        content={
            "action": "get_flight_deals",
            "query": "Find flights from NYC to Tokyo for next week"
        },
        metadata={"correlation_id": "platinum-req-001"}
    )
    add_secure_passport(platinum_request, platinum_passport)

    # Process the request through middleware
    auth_context = passport_middleware.process_request(platinum_request)
    print(f"Authorization Context: {auth_context}")
    print(f"Can book flights: {passport_middleware.can_perform('book_flights')}")
    print(f"Can access loyalty: {passport_middleware.can_perform('loyalty_access')}")

    # Scenario 2: Anonymous request (no passport)
    print("\n--- Scenario 2: Anonymous Request ---")

    anonymous_request = A2AMessage(
        type="task",
        content={
            "action": "get_flight_deals",
            "query": "Find cheap flights"
        }
    )

    auth_context = passport_middleware.process_request(anonymous_request)
    print(f"Authorization Context: {auth_context}")
    print(f"Can book flights: {passport_middleware.can_perform('book_flights')}")
    print(f"Can access loyalty: {passport_middleware.can_perform('loyalty_access')}")

    # Scenario 3: Invalid/tampered passport
    print("\n--- Scenario 3: Tampered Passport ---")

    tampered_passport = CallerContext(
        client_id="a2a://malicious-agent.fake",
        state={"tier": "Admin", "permissions": ["admin"]},
        signature="invalid-signature-attempt"  # Won't verify
    )

    tampered_request = A2AMessage(
        type="task",
        content={"action": "delete_all_data"}
    )
    add_secure_passport(tampered_request, tampered_passport)

    auth_context = passport_middleware.process_request(tampered_request)
    print(f"Tampered passport verified: {tampered_passport.is_verified}")
    print(f"Authorization Context: {auth_context}")

    print("\n" + "=" * 70)
    print("Demo complete! Run 'adk web' to interact with the agent.")
    print("=" * 70)
