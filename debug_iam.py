#!/usr/bin/env python3
"""Debug script for testing IAM role fetching."""

import asyncio
import logging
import sys

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from sequel.services.iam import get_iam_service


async def test_iam_roles():
    """Test IAM role fetching for a service account."""
    if len(sys.argv) < 3:
        print("Usage: python debug_iam.py <project_id> <service_account_email>")
        print("Example: python debug_iam.py my-project my-sa@my-project.iam.gserviceaccount.com")
        sys.exit(1)

    project_id = sys.argv[1]
    service_account_email = sys.argv[2]

    print(f"\n{'='*60}")
    print(f"Testing IAM role fetching")
    print(f"Project: {project_id}")
    print(f"Service Account: {service_account_email}")
    print(f"{'='*60}\n")

    try:
        iam_service = await get_iam_service()
        print("✓ IAM service initialized\n")

        print("Fetching roles (check logs above for details)...\n")
        roles = await iam_service.get_service_account_roles(
            project_id=project_id,
            service_account_email=service_account_email,
            use_cache=False  # Disable cache for testing
        )

        print(f"\n{'='*60}")
        print(f"Results: Found {len(roles)} role(s)")
        print(f"{'='*60}\n")

        if roles:
            for role in roles:
                print(f"  • {role.role}")
        else:
            print("  No roles found for this service account")
            print("\nPossible reasons:")
            print("  1. Service account has no project-level IAM bindings")
            print("  2. IAM API permission issue (check logs for errors)")
            print("  3. Service account email format mismatch")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_iam_roles())
