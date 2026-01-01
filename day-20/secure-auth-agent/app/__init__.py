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

"""Day 20: A2A Extensions - Secure Auth Agent"""

from .agent import root_agent, app
from .secure_passport_ext import (
    CallerContext,
    A2AMessage,
    add_secure_passport,
    get_secure_passport,
    has_secure_passport,
    SECURE_PASSPORT_EXTENSION_URI,
)

__all__ = [
    "root_agent",
    "app",
    "CallerContext",
    "A2AMessage",
    "add_secure_passport",
    "get_secure_passport",
    "has_secure_passport",
    "SECURE_PASSPORT_EXTENSION_URI",
]
