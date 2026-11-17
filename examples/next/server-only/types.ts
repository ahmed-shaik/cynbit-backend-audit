import "server-only";

export type CandidateApplicationInput = {
  jobId: string;
  fullName: string;
  email: string;
  skills: string[];
  statement: string;
  portfolioUrl?: string;
  linkedinUrl?: string;
};

export type RequestContext = {
  requestId: string;
  logger: {
    warn(event: string, fields: { requestId: string; errorType: string }): void;
  };
};

export type ApplicationService = {
  submitOnce(input: {
    application: CandidateApplicationInput;
    idempotencyToken: string;
    requestId: string;
  }): Promise<void>;
};

export type ApplicationAbuseControls = {
  checkApplicationSubmission(context: RequestContext): Promise<void>;
};
