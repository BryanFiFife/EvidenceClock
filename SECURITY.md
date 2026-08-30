# Security policy

EvidenceClock is a freshness and integrity precondition gate, not a truth oracle. Hashes prove that bytes are unchanged, not that evidence was correct when captured. `observed_at` should be supplied by a trusted runtime clock. File checks reject symlinks by default. Report vulnerabilities through a private GitHub Security Advisory.
