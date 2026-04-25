import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { getJob } from '../api/jobs';
import type { JobResponse } from '../types/job';

const STATUS_PROGRESS: Record<JobResponse['status'], number> = {
  PENDING: 15,
  RUNNING: 70,
  SUCCEEDED: 100,
  FAILED: 100,
};

const PIPELINE_STAGE_LABELS: Record<string, string> = {
  DOCUMENT_PARSING: 'Parsing your uploaded template and source document.',
  OUTLINE_PROMPT_GENERATION: 'Generating the outline prompt for the deck structure.',
  OUTLINE_PROMPT_READY: 'Outline prompt is ready and waiting for downstream slide generation.',
  SLIDE_DRAFTING: 'Drafting slide titles, bullets, tables, and chart candidates.',
  REVIEWING: 'Reviewing the generated slide draft for missing or oversized content.',
  CHART_RENDERING: 'Rendering chart images from chart-friendly spreadsheet data.',
  PPT_BUILDING: 'Building the PowerPoint file from the uploaded template.',
  RESULT_UPLOADING: 'Uploading the completed presentation.',
  RESULT_READY: 'Your presentation is ready for download.',
  DEMO_RESULT_READY: 'Your demo presentation is ready for download.',
};

const extractErrorMessage = (error: unknown) => {
  if (typeof error === 'object' && error !== null) {
    const maybeAxiosError = error as {
      response?: {
        data?: {
          error?: string;
        };
      };
      message?: string;
    };

    return maybeAxiosError.response?.data?.error || maybeAxiosError.message || 'Unable to load job status.';
  }

  return 'Unable to load job status.';
};

const formatTimestamp = (value?: string) => {
  if (!value) {
    return '-';
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

export default function JobStatusPage() {
  const navigate = useNavigate();
  const { jobId } = useParams();
  const [job, setJob] = useState<JobResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchJob = useCallback(async () => {
    if (!jobId) {
      setErrorMessage('Missing job identifier.');
      setIsLoading(false);
      return;
    }

    try {
      const nextJob = await getJob(jobId);
      setJob(nextJob);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(extractErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    void fetchJob();
  }, [fetchJob]);

  useEffect(() => {
    if (!jobId || !job || job.status === 'SUCCEEDED' || job.status === 'FAILED') {
      return;
    }

    const intervalId = window.setInterval(() => {
      void fetchJob();
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, [fetchJob, job, jobId]);

  const progress = job ? STATUS_PROGRESS[job.status] : 0;
  const isComplete = job?.status === 'SUCCEEDED';
  const isFailed = job?.status === 'FAILED';
  const statusLabel = job?.status || 'PENDING';
  const statusMessage = useMemo(() => {
    if (isLoading && !job) {
      return 'Loading the latest job state...';
    }
    if (isFailed) {
      return job?.errorMessage || 'The pipeline failed before a result could be produced.';
    }
    if (isComplete) {
      return 'Your presentation is ready.';
    }
    if (job?.status === 'PENDING') {
      return 'Preparing the pipeline and validating uploaded files.';
    }
    if (job?.pipelineStage && PIPELINE_STAGE_LABELS[job.pipelineStage]) {
      return PIPELINE_STAGE_LABELS[job.pipelineStage];
    }
    return 'Synthesizing architectural diagrams and layouts.';
  }, [isComplete, isFailed, isLoading, job]);

  const circumference = 2 * Math.PI * 88;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="min-h-[calc(100vh-160px)] w-full flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-xl">
        <div className="bg-surface-container-lowest rounded-xl p-8 md:p-12 border border-outline-variant/10 shadow-[0_20px_40px_rgba(0,31,63,0.06)] overflow-hidden relative">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-10">
            <div>
              <p className="text-xs font-bold tracking-widest text-on-surface-variant/60 uppercase font-label mb-1">Job Identifier</p>
              <h1 className="text-2xl font-extrabold text-primary-container font-headline tracking-tight">#{jobId || 'unknown'}</h1>
            </div>
            {isComplete ? (
              <span className="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-700 text-xs font-bold tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-2" />
                SUCCEEDED
              </span>
            ) : isFailed ? (
              <span className="inline-flex items-center px-3 py-1 rounded-full bg-red-100 text-red-700 text-xs font-bold tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 mr-2" />
                FAILED
              </span>
            ) : (
              <span className="inline-flex items-center px-3 py-1 rounded-full bg-primary-fixed text-on-primary-fixed text-xs font-bold font-label tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-surface-tint animate-pulse mr-2" />
                {statusLabel}
              </span>
            )}
          </div>

          <div className="flex flex-col items-center justify-center py-8 mb-10">
            <div className="relative w-48 h-48 mb-8">
              <svg className="w-full h-full transform -rotate-90">
                <circle className="text-surface-container-low" cx="96" cy="96" fill="transparent" r="88" strokeWidth="6" stroke="currentColor" />
                <circle
                  className={`transition-all duration-500 ease-out ${isFailed ? 'text-red-500' : 'text-primary-container'}`}
                  cx="96"
                  cy="96"
                  fill="transparent"
                  r="88"
                  strokeWidth="6"
                  stroke="currentColor"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-3xl font-extrabold font-headline text-primary-container tracking-tighter">{progress}%</span>
                <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label mt-1">Progress</span>
              </div>
            </div>

            <div className="text-center">
              <h2 className="text-lg font-bold text-on-surface font-headline mb-1">
                {isFailed ? 'Generation failed' : isComplete ? 'Complete!' : 'Generating slides...'}
              </h2>
              <p className="text-sm text-on-surface-variant font-body">{statusMessage}</p>
            </div>
          </div>

          <div className="space-y-4 mb-8">
            <div className="bg-surface-container-low rounded-lg p-5 flex items-center gap-4">
              <div className="bg-surface-container-highest p-2 rounded-lg">
                <span className="material-symbols-outlined text-primary-container">tactic</span>
              </div>
              <div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label">Pipeline Stage</p>
                <p className="text-sm font-semibold text-on-surface font-body">{job?.pipelineStage || statusLabel}</p>
              </div>
            </div>
            <div className="bg-surface-container-low rounded-lg p-5 flex items-center gap-4">
              <div className="bg-surface-container-highest p-2 rounded-lg">
                <span className="material-symbols-outlined text-primary-container">calendar_today</span>
              </div>
              <div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label">Created At</p>
                <p className="text-sm font-semibold text-on-surface font-body">{formatTimestamp(job?.createdAt)}</p>
              </div>
            </div>
            <div className="bg-surface-container-low rounded-lg p-5 flex items-center gap-4">
              <div className="bg-surface-container-highest p-2 rounded-lg">
                <span className="material-symbols-outlined text-primary-container">update</span>
              </div>
              <div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label">Updated At</p>
                <p className="text-sm font-semibold text-on-surface font-body">{formatTimestamp(job?.updatedAt)}</p>
              </div>
            </div>
          </div>

          {errorMessage && (
            <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {errorMessage}
            </div>
          )}

          <div className="flex flex-col gap-3">
            <button
              type="button"
              onClick={() => {
                if (job?.resultUrl) {
                  window.open(job.resultUrl, '_blank', 'noopener,noreferrer');
                }
              }}
              className={`premium-gradient w-full py-4 rounded-lg text-white font-bold font-label tracking-tight flex items-center justify-center gap-2 transition-all ${!isComplete || !job?.resultUrl ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02] shadow-md'}`}
              disabled={!isComplete || !job?.resultUrl}
            >
              <span className="material-symbols-outlined text-lg">download</span>
              Download Result PPT
            </button>
            <div className="flex justify-between items-center px-2 mt-2">
              <button
                type="button"
                onClick={() => {
                  if (isFailed) {
                    navigate('/upload');
                    return;
                  }
                  void fetchJob();
                }}
                className="text-on-surface-variant hover:text-primary-container text-sm font-semibold transition-colors flex items-center gap-1 group"
              >
                <span className="material-symbols-outlined text-base group-hover:rotate-180 transition-transform duration-500">refresh</span>
                {isFailed ? 'Back to Upload' : 'Refresh'}
              </button>
              <Link to="/history" className="text-primary-container hover:underline text-sm font-bold flex items-center gap-1">
                Back to History
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </Link>
            </div>
          </div>
        </div>

        <p className="text-center mt-10 text-xs font-medium text-on-surface-variant opacity-60 font-body">
          Large language models may take up to 2 minutes for complex presentations.
        </p>
      </div>
    </div>
  );
}
