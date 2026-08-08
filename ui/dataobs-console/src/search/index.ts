import { createRegistry } from "./registry";
import {
  assetProvider,
  dataProductProvider,
  monitorProvider,
} from "./providers/core";
export * from "./types";
export * from "./controller";
export * from "./ranking";
export * from "./privacyPolicy";
export const searchProviders = createRegistry([
  assetProvider,
  dataProductProvider,
  monitorProvider,
]);
