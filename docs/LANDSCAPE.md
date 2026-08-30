# Landscape

Stateful/temporal policy systems increasingly mention data freshness, but the mechanism is commonly platform-specific. EvidenceClock is a small vendor-neutral primitive: a portable evidence DAG with explicit observation time, maximum age, content digest and dependency propagation. It can sit underneath MCP, A2A, workflow engines or bespoke agents.
