# Kubernetes supply-chain admission contract

DataObs is policy-engine neutral. Production **must** pin every image by a non-placeholder digest from a configured allowed registry. An admission engine **should** additionally verify the existing release signature and provenance: repository identity `Jagadeeshck/DataObs`, the approved release workflow/builder identity, subject digest equality, and the corresponding SBOM/provenance envelope. Kubernetes alone does not verify signatures.

Use enforce mode for production and audit only for development. Kyverno, Gatekeeper, or another engine may implement the contract; none is installed by the chart. Registry patterns are operator inputs. Never place registry credentials in policy or reports. Evidence must retain digest, signature/provenance verification result and identity—not tokens or certificates.
