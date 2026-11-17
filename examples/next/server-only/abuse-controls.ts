import "server-only";

import type { ApplicationAbuseControls } from "./types";

let adapter: ApplicationAbuseControls | undefined;

/** Register shared rate-limit and anti-spam controls during server bootstrap. */
export function configureAbuseControls(controls: ApplicationAbuseControls): void {
  adapter = controls;
}

export const abuseControls: ApplicationAbuseControls = {
  async checkApplicationSubmission(context) {
    if (!adapter) throw new Error("Abuse-control adapter is not configured");
    await adapter.checkApplicationSubmission(context);
  },
};
