import { describe, expect, it } from "vitest";
import { buildRoutePath, consoleRoutes, visibleRoutes } from "../../app/routes";
import { canonicalRoles } from "./canonical";
import { presentPermission } from "./catalogue";

describe("administration access contract", () => {
  it("registers the complete hierarchy with canonical permissions", () => {
    const admin = consoleRoutes.filter((route) =>
      route.id.startsWith("administration"),
    );
    expect(admin.map((route) => route.id)).toHaveLength(8);
    expect(
      admin.find((route) => route.id === "administration-access-new")
        ?.requiredPermission,
    ).toBe("iam:write");
    expect(
      admin.find((route) => route.id === "administration-access")
        ?.requiredPermission,
    ).toBe("iam:read");
    expect(
      admin.every(
        (route) => route.owner === "team-5" && route.loadingLabel.length > 0,
      ),
    ).toBe(true);
  });
  it("keeps mutation navigation hidden and safely encodes binding identifiers", () => {
    expect(
      visibleRoutes(["auth:read"]).some(
        (route) => route.id === "administration-my-access",
      ),
    ).toBe(true);
    expect(
      visibleRoutes(["auth:read"]).some(
        (route) => route.id === "administration-access-new",
      ),
    ).toBe(false);
    expect(
      buildRoutePath("administration-access-detail", {
        bindingId: "binding/private value",
      }),
    ).toBe("/administration/access/binding%2Fprivate%20value");
  });
  it("uses only the canonical backend role catalogue", () => {
    expect(canonicalRoles).toEqual([
      "platform_admin",
      "tenant_admin",
      "operator",
      "investigator",
      "monitor_editor",
      "workflow_approver",
      "viewer",
      "collector",
    ]);
  });
  it("renders an explicit fallback for unknown canonical permissions", () => {
    expect(presentPermission("future:read").label).toContain("future:read");
    expect(presentPermission("iam:write").risk).toBe("high");
  });
});
