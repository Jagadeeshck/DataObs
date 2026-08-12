# Team 1 / Team 2 Data Product handoff

Team 1 publicly exposes canonical messaging references, explicit binding evidence, Product Exposure states and paths,
confidence/score explanations, bounded Known Consumers, and safe owner/SLO context read through `DataProductReadPort`.
Team 2 could consume this contract as a public pathway evidence adapter when composing `GET /data-products/{id}/impact`.

`DataProductImpactService` still reports both `lineage` and `pathways` as missing evidence. Closing the pathway gap
requires a Team 2-owned change that injects and reads Team 1's public adapter; it must not let Team 1 write private Team
2 storage. Equivalent output types for Kinesis, SQS, RabbitMQ, Pub/Sub, Event Hubs, and Service Bus also require Team 2
owner review. Until then Team 1 canonical references bridge them without changing Team 2's vocabulary.

Team 3 may consume counts for critical potential exposures, potential exposures, observed degradation, SLO impact,
highest authoritative criticality, confidence, and evidence refs; Team 3 alone decides incident implications. Team 5
may render the already-shaped state, confidence, criticality, owner, SLO, relationship, distance, and evidence status
using the terms Product Exposure, Potential Exposure, Observed Product Degradation, Product SLO Impact, Business
Criticality, and Known Consumers. Browser code must not traverse or rescore.
