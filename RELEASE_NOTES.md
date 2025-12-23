# VPC Networks and Subnets Support 🌐

This release adds support for browsing Google Cloud VPC Networks and their subnets in a hierarchical structure.

## New Features

### VPC Networks and Subnets
- **Hierarchical resource browsing**: Networks → Subnets
- **Network information**: Name, mode (auto/custom), subnet count, MTU, routing mode, creation time
- **Subnet information**: Name, region, IP CIDR range, gateway address, private Google access, flow logs, purpose
- **Visual indicators**: 🌐 for networks, 🔗 for subnets
- **Efficient loading**: Uses aggregatedList API to fetch all subnets in a single call

## Implementation Details

- Added VPCNetwork and Subnet models with comprehensive metadata
- Implemented NetworksService with caching and retry logic
- Integrated with resource tree for lazy loading and filtering
- Full test coverage: 27 new tests (9 model, 18 service)

## Statistics

- **Total Tests**: 605 (all passing)
- **Coverage**: 92.37%
- **New Files**: 4 (models, service, tests)
- **Modified Files**: 6

## Supported Resources

Sequel now supports **11 resource categories**:
1. Cloud DNS (zones → records)
2. Cloud SQL instances
3. Compute Instance Groups (groups → instances)
4. GKE Clusters (clusters → nodes)
5. Secrets
6. Service Accounts (accounts → role bindings)
7. Firewall Policies
8. Cloud Storage Buckets
9. Pub/Sub (topics → subscriptions)
10. Cloud Run (services and jobs)
11. **VPC Networks (networks → subnets)** ✨ NEW

## Installation

\`\`\`bash
pip install sequel-ag==1.4.0
\`\`\`

Or upgrade from a previous version:

\`\`\`bash
pip install --upgrade sequel-ag
\`\`\`

## Full Changelog

**Merged PRs:**
- #25: Add VPC Networks and Subnets support

**Commits:**
- docs: Add VPC Networks to implementation plan
- feat: Add VPC Network and Subnet models
- feat: Add VPC Networks service
- feat: Add VPC Networks state management
- feat: Integrate VPC Networks with resource tree
- test: Add comprehensive model and service tests
- docs: Update documentation for v1.4.0
- chore: Bump version to 1.4.0

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
