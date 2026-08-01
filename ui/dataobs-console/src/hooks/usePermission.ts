import type { Permission } from "../api/common";
export function usePermission(
  granted: readonly Permission[],
  required: Permission,
): boolean {
  return granted.includes(required);
}
