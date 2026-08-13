import type { CapabilityState, MessagingProviderEvidence } from "./types";

export const capabilityState = (
  provider: MessagingProviderEvidence,
  capability: string,
): CapabilityState => {
  if (
    !provider.configured ||
    provider.collection_capability === "not_configured"
  )
    return "not_configured";
  if (
    [provider.runtime_state, provider.collection_capability].includes(
      "unavailable",
    )
  )
    return "unavailable";
  const value = provider.capabilities[capability];
  if (value === "partial") return "partial";
  if (value === true || value === "supported") return "supported";
  return "unsupported";
};

export const capabilityStateLabel: Record<CapabilityState, string> = {
  supported: "Supported",
  partial: "Partial",
  not_configured: "Not configured",
  unavailable: "Unavailable",
  unsupported: "Not applicable",
};
