import { UserManager, WebStorageStateStore } from "oidc-client-ts";

export type PublicAuthConfig = {
  provider: string;
  issuer?: string;
  client_id?: string;
  authorization_endpoint?: string;
  scopes: string[];
};

let manager: UserManager | undefined;
export async function userManager() {
  if (manager) return manager;
  const response = await fetch("/api/v1/auth/config", {
    credentials: "same-origin",
  });
  if (!response.ok) throw new Error("Authentication configuration unavailable");
  const config = (await response.json()) as PublicAuthConfig;
  if (config.provider !== "oidc" || !config.issuer || !config.client_id)
    throw new Error("OIDC authentication is not configured");
  manager = new UserManager({
    authority: config.issuer,
    client_id: config.client_id,
    redirect_uri: `${location.origin}/auth/callback`,
    post_logout_redirect_uri: `${location.origin}/login`,
    response_type: "code",
    scope: [
      "openid",
      ...config.scopes.filter((scope) => scope !== "openid"),
    ].join(" "),
    userStore: new WebStorageStateStore({ store: sessionStorage }),
    automaticSilentRenew: false,
  });
  return manager;
}

export async function accessToken() {
  try {
    const user = await (await userManager()).getUser();
    return user && !user.expired ? user.access_token : undefined;
  } catch {
    return undefined;
  }
}
