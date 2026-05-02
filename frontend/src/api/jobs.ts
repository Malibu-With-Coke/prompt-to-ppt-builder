import axios from 'axios';
import apiClient from './client';
import type { JobResponse, JobSummary } from '../types/job';

export interface UploadUrlRequest {
  jobId: string;
  fileType: 'template' | 'content';
  fileName: string;
  contentType: string;
  fileIndex?: number;
}

export interface UploadUrlResponse {
  uploadUrl: string;
  s3Key: string;
}

export interface CreateJobRequest {
  jobId: string;
  templateS3Key?: string;
  contentS3Key?: string;
  contentS3Keys?: string[];
  demoPreset?: 'excel';
  options: {
    tone: string;
    target: string;
    length: number;
    notes?: string;
    aiEngine: 'bedrock' | 'openai';
  };
}

export interface CreateJobResponse {
  jobId: string;
  status: 'PENDING' | 'SUCCEEDED';
  createdAt: string;
  demoPreset?: 'excel';
}

export const requestUploadUrl = async (payload: UploadUrlRequest) => {
  const response = await apiClient.post<UploadUrlResponse>('/jobs/upload-url', payload);
  return response.data;
};

export const uploadFileToS3 = async (uploadUrl: string, file: File) => {
  await axios.put(uploadUrl, file, {
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
    },
  });
};

export const createJob = async (payload: CreateJobRequest) => {
  const response = await apiClient.post<CreateJobResponse>('/jobs', payload);
  return response.data;
};

export const getJob = async (jobId: string) => {
  const response = await apiClient.get<JobResponse>(`/jobs/${jobId}`);
  return response.data;
};

export const listJobs = async () => {
  const response = await apiClient.get<{ jobs: JobSummary[] }>('/jobs');
  return response.data.jobs;
};
