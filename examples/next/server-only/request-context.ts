import "server-only";

import { randomUUID } from "node:crypto";
import type { RequestContext } from "./types";

export async function getRequestContext(): Promise<RequestContext> {
  const requestId = randomUUID();
  return {
    requestId,
    logger: {
      warn(event, fields) {
        // A production logger should keep this allowlisted shape and avoid request data.
        console.warn(JSON.stringify({ event, requestId: fields.requestId, errorType: fields.errorType }));
      },
    },
  };
}
