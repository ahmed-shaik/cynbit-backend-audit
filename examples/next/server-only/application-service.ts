import "server-only";

import type { ApplicationService } from "./types";

let adapter: ApplicationService | undefined;

/** Register a durable, transaction-backed implementation during server bootstrap. */
export function configureApplicationService(service: ApplicationService): void {
  adapter = service;
}

export const applicationService: ApplicationService = {
  async submitOnce(input) {
    if (!adapter) throw new Error("Application service adapter is not configured");
    await adapter.submitOnce(input);
  },
};
