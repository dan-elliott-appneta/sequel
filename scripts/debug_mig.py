#!/usr/bin/env python3
"""Debug script to test managed instance group API calls."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sequel.services.compute import get_compute_service


async def debug_instance_groups(project_id: str):
    """Debug instance group listing."""
    print(f"\n=== Debugging Instance Groups for {project_id} ===\n")

    service = await get_compute_service()

    # List all instance groups
    print("1. Listing all instance groups...")
    groups = await service.list_instance_groups(project_id, use_cache=False)

    print(f"   Found {len(groups)} instance groups\n")

    for group in groups:
        print(f"Group: {group.group_name}")
        print(f"  Managed: {group.is_managed}")
        print(f"  Size: {group.size}")

        if hasattr(group, 'zone') and group.zone:
            zone_parts = group.zone.split('/')
            zone = zone_parts[-1] if zone_parts else None
            print(f"  Type: Zonal")
            print(f"  Zone: {zone}")

            # Try to list instances
            print(f"  Listing instances...")
            try:
                instances = await service.list_instances_in_group(
                    project_id=project_id,
                    zone=zone,
                    instance_group_name=group.group_name,
                    is_managed=group.is_managed,
                    use_cache=False,
                )
                print(f"  ✓ Found {len(instances)} instances")
                for inst in instances:
                    print(f"    - {inst.name} ({inst.status})")
            except Exception as e:
                print(f"  ✗ Error: {e}")

        elif hasattr(group, 'region') and group.region:
            region_parts = group.region.split('/')
            region = region_parts[-1] if region_parts else None
            print(f"  Type: Regional")
            print(f"  Region: {region}")

            # Try to list instances
            print(f"  Listing instances...")
            try:
                instances = await service.list_instances_in_regional_group(
                    project_id=project_id,
                    region=region,
                    instance_group_name=group.group_name,
                    is_managed=group.is_managed,
                    use_cache=False,
                )
                print(f"  ✓ Found {len(instances)} instances")
                for inst in instances:
                    print(f"    - {inst.name} ({inst.status})")
            except Exception as e:
                print(f"  ✗ Error: {e}")

        print()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_mig.py PROJECT_ID")
        print("\nExample: python scripts/debug_mig.py my-project-123")
        sys.exit(1)

    project_id = sys.argv[1]
    await debug_instance_groups(project_id)


if __name__ == "__main__":
    asyncio.run(main())
