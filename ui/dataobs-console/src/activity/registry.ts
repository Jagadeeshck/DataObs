import { incidentActivityProvider } from "./providers";
import type { ActivityProvider } from "./types";
export const activityProviders: readonly ActivityProvider[] = [
  incidentActivityProvider,
];
export function validateActivityRegistry(providers = activityProviders) {
  const ids = new Set<string>();
  providers.forEach((provider) => {
    if (ids.has(provider.id))
      throw new Error(`Duplicate activity provider: ${provider.id}`);
    ids.add(provider.id);
    if (provider.maximumItems < 1 || provider.maximumItems > 50)
      throw new Error(`Unbounded provider: ${provider.id}`);
    if (provider.timeoutMs < 100 || provider.timeoutMs > 4_000)
      throw new Error(`Invalid provider timeout: ${provider.id}`);
    if (!provider.requiredPermission)
      throw new Error(`Missing provider permission: ${provider.id}`);
  });
  return true;
}
