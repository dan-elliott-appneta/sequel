# GCP Resources for Sequel - Ranked by Implementation Difficulty

## Executive Summary

Based on exploration of the Sequel codebase, I've identified the implementation pattern for adding new GCP resources and ranked 25+ potential resources by ease of implementation. The ranking considers API complexity, hierarchical structure, region querying requirements, and likely stability issues.

## Current Implementation Status

**Currently Supported (9 categories):**
1. Cloud DNS (zones → records) - Complex hierarchical
2. Cloud SQL instances - Simple flat
3. Cloud Storage Buckets - Simple flat
4. Pub/Sub Topics → Subscriptions - Complex hierarchical
5. Compute Instance Groups (groups → instances) - Complex hierarchical
6. GKE Clusters (clusters → nodes) - Complex hierarchical
7. Secrets - Simple flat
8. Service Accounts (accounts → role bindings) - Complex hierarchical
9. Firewall Policies - Simple flat

## Implementation Pattern Summary

**Simple Resources** (3-4 hours each):
- Single API call per project
- Flat structure, no sub-resources
- Model → Service → State → Tree (4 files + tests)

**Complex Resources** (2-3 days each):
- Multiple API levels (parent → children)
- Hierarchical tree expansion
- 2 models, complex state management

**Key Difficulty Factors:**
1. API pagination requirements
2. Regional vs global resources (regional = harder due to 30+ queries)
3. Hierarchical depth (single level vs multi-level)
4. Special authentication/permissions
5. API stability (learned from load balancer issues)

---

## Ranked Resources (Easiest → Hardest)

### ⭐ TIER 1: Very Easy (3-4 hours)
Single API call, flat structure, no sub-resources

#### 1. **Cloud Storage Buckets** 🥇
**Difficulty: 1/10**
- API: `storage.buckets().list(project=project_id)`
- Structure: Flat list per project
- Fields: name, location, storage class, creation time, size
- Why easy: Simple API, no regions, no sub-resources
- Similar to: Secrets, CloudSQL
- **Recommended first addition**

#### 2. **Persistent Disks**
**Difficulty: 2/10**
- API: `compute.disks().aggregatedList(project=project_id)`
- Structure: Flat list (aggregated across zones)
- Fields: name, size, type, zone, status, attached instances
- Why easy: Aggregated API avoids region queries
- Similar to: CloudSQL instances
- Note: Shows which instances they're attached to

#### 3. **VPC Networks**
**Difficulty: 2/10**
- API: `compute.networks().list(project=project_id)`
- Structure: Flat list (global resource)
- Fields: name, mode (auto/custom), subnets count, peerings
- Why easy: Global resource, single API call
- Similar to: Firewall policies
- Potential child: Subnets (makes it tier 3)

#### 4. **Cloud Functions (Gen 2)**
**Difficulty: 3/10**
- API: `cloudfunctions.projects().locations().functions().list()`
- Structure: Per-location, but can use `-` wildcard for all
- Fields: name, runtime, trigger type, state, region
- Why easy: Wildcard location query avoids iteration
- Similar to: Secrets
- Note: Gen 2 uses Cloud Run under the hood

#### 5. **Cloud Run Services**
**Difficulty: 3/10**
- API: `run.projects().locations().services().list()`
- Structure: Per-location, supports `-` wildcard
- Fields: name, image, URL, status, region, traffic allocation
- Why easy: Wildcard location support
- Similar to: Cloud Functions
- Popular serverless option

**Implementation Plan (v1.3.0):** ⚙️ **IN PROGRESS**
- Create CloudRunService and CloudRunJob models in `src/sequel/models/cloudrun.py`
- Implement CloudRunService with list_services() and list_jobs()
- Add flat tree structure with separate nodes for Services and Jobs
- Use icons: ☁️ for services, ⚙️ for jobs
- Show service URL, image, status, and traffic allocation
- Show job execution count, last run time, and status

#### 5a. **Cloud Run Jobs**
**Difficulty: 3/10**
- API: `run.projects().locations().jobs().list()`
- Structure: Per-location, supports `-` wildcard
- Fields: name, image, status, region, last execution time, execution count
- Why easy: Wildcard location support, same API as Cloud Run Services
- Similar to: Cloud Run Services
- Batch processing option

#### 6. **SSL Certificates**
**Difficulty: 3/10**
- API: `compute.sslCertificates().list(project=project_id)`
- Structure: Flat list (global resource)
- Fields: name, domains, expiration, type (managed/self-signed)
- Why easy: Global resource, simple API
- Similar to: Firewall policies
- Useful: Shows certificate expiration dates

---

### ⭐ TIER 2: Easy (1 day)
Single level hierarchy or simple multi-region

#### 7. **Cloud Storage Buckets → Objects**
**Difficulty: 4/10**
- APIs: `storage.buckets().list()` + `storage.objects().list(bucket=name)`
- Structure: Buckets (parent) → Objects (children, paginated)
- Why medium: Object listing can be huge (need limits)
- Similar to: CloudDNS zones → records
- Consideration: Limit to first 100 objects per bucket

#### 8. **Snapshots**
**Difficulty: 4/10**
- API: `compute.snapshots().list(project=project_id)`
- Structure: Flat list (global resource)
- Fields: name, source disk, size, creation time, storage bytes
- Why easy: Global resource, straightforward
- Similar to: Persistent disks
- Useful: Shows backup status

#### 9. **Cloud KMS Keyrings**
**Difficulty: 4/10**
- API: `cloudkms.projects().locations().keyRings().list()`
- Structure: Per-location, but limited locations (~10)
- Fields: name, location, creation time
- Why medium: Multi-location but manageable
- Similar to: Cloud Functions (fewer locations)
- Potential child: Crypto keys (makes it tier 3)

#### 10. **Memorystore Redis Instances**
**Difficulty: 5/10**
- API: `redis.projects().locations().instances().list()`
- Structure: Per-location, ~30 regions
- Fields: name, tier, memory size, version, state, host/port
- Why medium: Regional resource but common service
- Similar to: CloudSQL (same pattern)
- Consideration: Use aggregated pattern if available

---

### ⭐ TIER 3: Moderate (2-3 days)
Hierarchical with sub-resources or complex structure

#### 11. **Subnets** (child of VPC Networks)
**Difficulty: 5/10**
- API: `compute.networks().list()` + `compute.subnetworks().list(region=r)`
- Structure: Networks → Subnets (per region)
- Why moderate: Requires region iteration per network
- Similar to: Compute groups → instances
- Parent: VPC Networks (tier 1 resource)

#### 12. **Routes**
**Difficulty: 5/10**
- API: `compute.routes().list(project=project_id)`
- Structure: Flat but associated with networks
- Fields: name, network, dest range, next hop, priority
- Why moderate: Complex routing logic to display
- Similar to: Firewall policies
- Display challenge: Showing routing topology

#### 13. **BigQuery Datasets**
**Difficulty: 5/10**
- API: `bigquery.datasets().list(projectId=project_id)`
- Structure: Flat list per project
- Fields: name, location, creation time, labels
- Why easy: Simple API
- Similar to: Cloud Storage buckets
- Potential child: Tables (makes it tier 4)

#### 14. **BigQuery Datasets → Tables**
**Difficulty: 6/10**
- APIs: `bigquery.datasets().list()` + `bigquery.tables().list(datasetId=id)`
- Structure: Datasets (parent) → Tables (children)
- Fields (tables): name, type, rows, size, creation time
- Why moderate: Two-level hierarchy, table metadata detailed
- Similar to: CloudDNS zones → records
- Popular data warehouse service

#### 15. **Pub/Sub Topics**
**Difficulty: 6/10**
- API: `pubsub.projects().topics().list(project=project_id)`
- Structure: Flat list
- Fields: name, labels, schema, message retention
- Why easy: Simple API
- Similar to: Secrets
- Potential child: Subscriptions (makes it tier 4)

#### 16. **Pub/Sub Topics → Subscriptions**
**Difficulty: 6/10**
- APIs: `pubsub.topics().list()` + `pubsub.subscriptions().list(project=id)`
- Structure: Topics → Subscriptions
- Why moderate: Subscriptions can belong to multiple topics
- Similar to: IAM accounts → bindings
- Complex: Many-to-many relationship

**Implementation Plan (v1.2.0):**
- Create Topic and Subscription models in `src/sequel/models/pubsub.py`
- Implement PubSubService with list_topics() and list_subscriptions()
- Add hierarchical tree structure: Topics (expandable) → Subscriptions (leaf nodes)
- Handle topic-subscription relationship (subscriptions reference their topic)
- Use icons: 📢 for topics, 📬 for subscriptions
- Follow Cloud DNS pattern for hierarchical expansion

---

### ⭐ TIER 4: Hard (3-5 days)
Complex hierarchies, many regions, or special handling

#### 17. **Cloud Armor Security Policies**
**Difficulty: 7/10**
- API: `compute.securityPolicies().list(project=project_id)`
- Structure: Policies → Rules (complex nested structure)
- Fields: name, rules (priority, action, match conditions)
- Why hard: Complex rule structures, WAF patterns
- Similar to: Firewall but more complex
- Display challenge: Showing rule logic clearly

#### 18. **KMS Keyrings → Crypto Keys**
**Difficulty: 7/10**
- APIs: Multiple levels - keyrings, keys, versions
- Structure: Keyrings → Crypto Keys → Key Versions
- Why hard: 3-level hierarchy, rotation management
- Similar to: GKE clusters → nodes, but more levels
- Security sensitive: Careful with display

#### 19. **App Engine Services**
**Difficulty: 7/10**
- API: `appengine.apps().services().list(appsId=project_id)`
- Structure: Services → Versions → Instances
- Why hard: 3-level hierarchy, complex deployment model
- Similar to: GKE but different paradigm
- Legacy service: Lower priority

#### 20. **Cloud Monitoring Alert Policies**
**Difficulty: 8/10**
- API: `monitoring.projects().alertPolicies().list(name=project_path)`
- Structure: Complex nested conditions and notifications
- Fields: name, conditions, notification channels, thresholds
- Why hard: Very complex object structure
- Display challenge: Summarizing alert logic
- Similar to: Cloud Armor (complex rules)

#### 21. **VPN Gateways → Tunnels**
**Difficulty: 8/10**
- APIs: `compute.vpnGateways().list()` + `compute.vpnTunnels().list()`
- Structure: Regional gateways → Tunnels
- Why hard: Regional iteration + complex connection state
- Similar to: Subnets but more complex
- Networking: Lower user demand

---

### ⭐ TIER 5: Very Hard (5+ days)
Multi-region iteration, deep hierarchies, or high complexity

#### 22. **Cloud NAT Configurations**
**Difficulty: 8/10**
- API: `compute.routers().list()` + router NAT configs
- Structure: Regional routers → NAT configurations
- Why hard: Embedded in routers, complex port allocation
- Requires: Understanding router concepts
- Similar to: VPN but more complex

#### 23. **Network Endpoint Groups (NEGs)**
**Difficulty: 9/10**
- API: `compute.networkEndpointGroups().list()`
- Structure: Regional, with individual endpoints
- Why hard: Regional iteration + complex endpoint management
- Similar to: Instance groups but more abstract
- Advanced networking: Niche use case

#### 24. **Dataflow Jobs**
**Difficulty: 9/10**
- API: `dataflow.projects().locations().jobs().list()`
- Structure: Per-region, complex job state
- Why hard: Regional queries, streaming vs batch, complex metrics
- Display challenge: Real-time job status
- Similar to: GKE but with live metrics

#### 25. **Organization Policies**
**Difficulty: 9/10**
- API: `orgpolicy.projects().policies().list(parent=project_path)`
- Structure: Hierarchical inheritance from org/folder
- Why hard: Requires org-level permissions, complex inheritance
- Permissions: Many users don't have org access
- Advanced: Enterprise feature

---

### ⚠️ TIER 6: Avoid
Resources with known stability issues or extreme complexity

#### 26. **Load Balancers** ❌
**Difficulty: 10/10 - UNSTABLE**
- **Status: REMOVED in v1.0.6**
- Why avoid: Thread-safety issues in googleapiclient
- Issues: Segfaults, memory corruption, UI hangs
- Requires: 30+ region queries = high concurrency
- Lesson learned: Regional resources with many locations are risky

#### 27. **Interconnects/Direct Peering** ❌
**Difficulty: 10/10**
- Why avoid: Enterprise-only, complex networking
- Limited user base: Very few users have interconnects
- Complex: Physical hardware concepts
- Similar to: Load balancers (regional complexity)

---

## Recommendations

### Top 5 to Add Next (Best ROI)

1. ✅ **Cloud Storage Buckets** (Tier 1) - Universal need, very easy - **COMPLETED v1.1.0**
2. ✅ **Pub/Sub Topics → Subscriptions** (Tier 3) - Messaging backbone - **COMPLETED v1.2.0**
3. ⚙️ **Cloud Run Services & Jobs** (Tier 1) - Modern serverless, popular - **IN PROGRESS v1.3.0**
4. **Persistent Disks** (Tier 1) - Shows compute storage, easy
5. **BigQuery Datasets → Tables** (Tier 3) - Data analytics, high value

### Implementation Strategy

**Phase 1: Quick Wins** (1 week)
- Add all Tier 1 resources (6 resources, 3-4 hours each)
- High user value, low risk
- Builds confidence with pattern

**Phase 2: High-Value Features** (2 weeks)
- BigQuery Datasets → Tables (Tier 3)
- Pub/Sub Topics → Subscriptions (Tier 3)
- Most requested by data engineers

**Phase 3: Completeness** (ongoing)
- Tier 2 and Tier 3 resources as needed
- Based on user feedback
- Avoid Tier 5+ until proven demand

### Risk Mitigation

**Avoid:**
- Resources requiring 20+ region queries (load balancer lesson)
- Deep hierarchies (3+ levels) until pattern proven
- Enterprise-only features (limited user base)

**Test:**
- All new resources with 50+ items (virtual scrolling)
- Regional resources with Semaphore limiting
- Memory usage during large dataset loads

## Critical Files for Implementation

For any new resource "example":

**Required:**
- `src/sequel/models/example.py` - Model class(es)
- `src/sequel/services/example.py` - Service class
- `src/sequel/state/resource_state.py` - Add methods
- `src/sequel/widgets/resource_tree.py` - Add node types + handlers
- `tests/unit/models/test_example.py` - Model tests
- `tests/unit/services/test_example.py` - Service tests

**Pattern reference files:**
- `src/sequel/models/firewall.py` - Simple flat resource
- `src/sequel/models/clouddns.py` - Complex hierarchical
- `src/sequel/services/cloudsql.py` - Simple service
- `src/sequel/services/clouddns.py` - Hierarchical service

---

## Conclusion

The easiest additions are **Cloud Storage Buckets, Persistent Disks, VPC Networks, Cloud Functions, and Cloud Run Services** - all Tier 1 resources requiring only 3-4 hours each.

The highest value additions are **BigQuery and Pub/Sub** (Tier 3) despite being more complex, as they're core GCP services.

Avoid resources requiring extensive regional iteration (Tier 5+) due to stability risks learned from the load balancer experience.
