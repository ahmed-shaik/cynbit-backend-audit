"use server";

import { z } from "zod";
import { applicationService } from "./server-only/application-service";
import { abuseControls } from "./server-only/abuse-controls";
import { getRequestContext } from "./server-only/request-context";

const httpsUrl = z
  .string()
  .trim()
  .url()
  .max(2_048)
  .refine((value) => {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && !parsed.username && !parsed.password;
  });

const ApplicationSchema = z.object({
  // Issued with this form by the server and consumed by the durable service.
  // It is retry metadata only; it never grants access to an application record.
  submissionToken: z.string().uuid().refine((value) => {
    const version = value.split("-")[2]?.[0];
    return version === "4";
  }),
  jobId: z.string().trim().min(1).max(80).regex(/^[A-Za-z0-9_-]+$/),
  fullName: z.string().trim().min(2).max(120),
  email: z.string().trim().email().max(254),
  skills: z.array(z.string().trim().min(1).max(48)).min(1).max(12),
  statement: z.string().trim().min(20).max(3_000),
  portfolioUrl: z.union([httpsUrl, z.literal("")]).optional(),
  linkedinUrl: z.union([httpsUrl, z.literal("")]).optional(),
});

function text(formData: FormData, key: string): string | undefined {
  const value = formData.get(key);
  return typeof value === "string" ? value : undefined;
}

export type ActionResult =
  | { ok: true; requestId: string }
  | { ok: false; code: "invalid_input" | "submission_unavailable"; fields?: string[] };

/**
 * Architectural example only. The adapters must be server-only, durable, and wired
 * to the deployment's trusted proxy and authentication configuration.
 */
export async function submitCandidateApplication(formData: FormData): Promise<ActionResult> {
  const parsed = ApplicationSchema.safeParse({
    submissionToken: text(formData, "submissionToken"),
    jobId: text(formData, "jobId"),
    fullName: text(formData, "fullName"),
    email: text(formData, "email"),
    skills: formData.getAll("skills").filter((value): value is string => typeof value === "string"),
    statement: text(formData, "statement"),
    portfolioUrl: text(formData, "portfolioUrl") || undefined,
    linkedinUrl: text(formData, "linkedinUrl") || undefined,
  });

  if (!parsed.success) {
    const fields = [...new Set(parsed.error.issues.map((issue) => String(issue.path[0] ?? "form")))];
    return { ok: false, code: "invalid_input", fields };
  }

  const context = await getRequestContext();
  try {
    await abuseControls.checkApplicationSubmission(context);
    // The service checks that the role is open, consumes a server-issued one-time
    // submission token, inserts the application and outbox event in one transaction,
    // and enforces a unique idempotency key. No client-supplied ID grants record access.
    const { submissionToken, ...application } = parsed.data;
    await applicationService.submitOnce({
      application,
      idempotencyToken: submissionToken,
      requestId: context.requestId,
    });
    return { ok: true, requestId: context.requestId };
  } catch (error) {
    // Send only a redacted event to general logs; detailed diagnostics belong in a
    // restricted error channel with PII scrubbing. Do not return exception text.
    context.logger.warn("candidate_submission_failed", {
      requestId: context.requestId,
      errorType: error instanceof Error ? error.name : "unknown",
    });
    return { ok: false, code: "submission_unavailable" };
  }
}
