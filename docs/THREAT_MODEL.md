# Threat model

EvidenceClock addresses stale-input execution: an agent makes a decision from evidence A, B and C, but one prerequisite expires or changes before the decision is used. The effective expiry of a derived node is the earliest expiry anywhere in its dependency graph.

It does not establish factual truth, source authenticity, remote freshness, or host integrity. Capture evidence through trusted adapters and verify immediately before a privileged action.
