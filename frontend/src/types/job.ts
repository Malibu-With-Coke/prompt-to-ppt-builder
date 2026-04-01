export interface JobResponse {
  jobId: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
  createdAt: string;
  updatedAt: string;
  pipelineStage?: string;
  errorMessage?: string;
  resultUrl?: string;
}

export interface JobSummary {
  jobId: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
  createdAt: string;
  updatedAt: string;
}
