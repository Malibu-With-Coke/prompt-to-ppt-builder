import { useState } from 'react';
import type { ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createJob, requestUploadUrl, uploadFileToS3 } from '../api/jobs';
import type { CreateJobRequest } from '../api/jobs';
import { useJobStore } from '../stores/jobStore';
import type { AIEngine, Audience, Length, Tone } from '../stores/jobStore';

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;
const lengthToSlideCount: Record<Length, number> = {
  '5 slides': 5,
  '10 slides': 10,
  '15 slides': 15,
};

const getFileExtension = (fileName: string) => {
  const segments = fileName.toLowerCase().split('.');
  return segments.length > 1 ? `.${segments.at(-1)}` : '';
};

const validateSelectedFile = (file: File, fileType: 'template' | 'content') => {
  const extension = getFileExtension(file.name);
  const allowedExtensions = fileType === 'template' ? ['.pptx'] : ['.docx', '.xlsx'];

  if (!allowedExtensions.includes(extension)) {
    return `${fileType === 'template' ? 'Template' : 'Content'} file must be ${allowedExtensions.join(' or ')}.`;
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return 'Each file must be 50MB or smaller.';
  }

  return null;
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

    return maybeAxiosError.response?.data?.error || maybeAxiosError.message || 'Something went wrong while creating the job.';
  }

  return 'Something went wrong while creating the job.';
};

export default function UploadPage() {
  const navigate = useNavigate();
  const {
    setCurrentJobId,
    tone,
    setTone,
    audience,
    setAudience,
    length,
    setLength,
    aiEngine,
    setAIEngine,
  } = useJobStore();
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [contentFile, setContentFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const buildJobOptions = (): CreateJobRequest['options'] => ({
    tone,
    target: audience,
    length: lengthToSlideCount[length],
    notes: '',
    aiEngine: aiEngine === 'OpenAI' ? 'openai' : 'bedrock',
  });

  const handleFileChange = (fileType: 'template' | 'content') => (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    event.target.value = '';

    if (!selectedFile) {
      return;
    }

    const validationError = validateSelectedFile(selectedFile, fileType);
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setErrorMessage(null);
    if (fileType === 'template') {
      setTemplateFile(selectedFile);
      return;
    }

    setContentFile(selectedFile);
  };

  const handleGenerateClick = async () => {
    if (!templateFile || !contentFile) {
      setErrorMessage('Please select both a template PPTX and a content document before generating.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setUploadProgress(5);

    const jobId = crypto.randomUUID();

    try {
      const [templateUpload, contentUpload] = await Promise.all([
        requestUploadUrl({
          jobId,
          fileType: 'template',
          fileName: templateFile.name,
          contentType: templateFile.type || 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        }),
        requestUploadUrl({
          jobId,
          fileType: 'content',
          fileName: contentFile.name,
          contentType: contentFile.type || 'application/octet-stream',
        }),
      ]);

      setUploadProgress(25);

      await Promise.all([
        uploadFileToS3(templateUpload.uploadUrl, templateFile),
        uploadFileToS3(contentUpload.uploadUrl, contentFile),
      ]);

      setUploadProgress(75);

      const job = await createJob({
        jobId,
        templateS3Key: templateUpload.s3Key,
        contentS3Key: contentUpload.s3Key,
        options: buildJobOptions(),
      });

      setUploadProgress(100);
      setCurrentJobId(job.jobId);
      navigate(`/jobs/${job.jobId}`);
    } catch (error) {
      setUploadProgress(0);
      setErrorMessage(extractErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoGenerateClick = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    setUploadProgress(15);

    const jobId = crypto.randomUUID();

    try {
      const job = await createJob({
        jobId,
        demoPreset: 'excel',
        options: buildJobOptions(),
      });

      setUploadProgress(100);
      setCurrentJobId(job.jobId);
      navigate(`/jobs/${job.jobId}`);
    } catch (error) {
      setUploadProgress(0);
      setErrorMessage(extractErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const canSubmit = Boolean(templateFile && contentFile) && !isSubmitting;

  return (
    <div className="w-full flex justify-center">
      <div className="flex-grow pb-16 w-full max-w-6xl mx-auto mt-12 mb-8 px-4 sm:px-6">
        <div className="mb-12 text-center md:text-left">
          <h1 className="text-4xl font-extrabold tracking-tight font-headline text-primary mb-2">Create New Deck</h1>
          <p className="text-on-surface-variant text-lg">Upload your assets and configure your architectural output.</p>
        </div>

        <section className="mb-8 rounded-xl border border-primary-container/20 bg-[linear-gradient(135deg,rgba(1,73,134,0.08),rgba(0,31,63,0.02))] p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-container/80">Demo Mode</p>
              <h2 className="mt-1 text-2xl font-bold text-primary font-headline">Start with the built-in sample deck</h2>
              <p className="mt-2 max-w-2xl text-sm text-on-surface-variant">
                Skip file uploads and generate a presentation from a bundled demo template plus sample Excel data.
              </p>
            </div>
            <button
              type="button"
              onClick={handleDemoGenerateClick}
              disabled={isSubmitting}
              className={`inline-flex min-w-[260px] items-center justify-center gap-3 rounded-xl px-6 py-4 font-bold text-white shadow-lg transition-all ${isSubmitting ? 'cursor-not-allowed bg-primary-container/60' : 'premium-gradient hover:scale-[1.02]'}`}
            >
              <span className="material-symbols-outlined">slideshow</span>
              {isSubmitting ? 'Preparing Demo...' : 'Try Demo PPT'}
            </button>
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          <div className="group relative flex flex-col items-center justify-center p-12 bg-surface-container-low rounded-xl cursor-pointer hover:bg-surface-container-high transition-all border-2 border-dashed border-outline-variant hover:border-primary-container">
            <div className="w-16 h-16 bg-surface-container-highest rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-primary-container text-3xl">upload_file</span>
            </div>
            <h3 className="text-lg font-bold font-headline text-primary mb-2">Template PPTX</h3>
            <p className="text-sm text-center text-on-surface-variant max-w-[240px]">
              {templateFile ? templateFile.name : 'Drag and drop your master slide deck or corporate theme'}
            </p>
            {templateFile && (
              <button
                type="button"
                onClick={() => setTemplateFile(null)}
                className="mt-4 text-xs font-semibold text-primary-container hover:underline z-10"
              >
                Remove file
              </button>
            )}
            <input className="absolute inset-0 opacity-0 cursor-pointer" type="file" accept=".pptx" onChange={handleFileChange('template')} />
          </div>

          <div className="group relative flex flex-col items-center justify-center p-12 bg-surface-container-low rounded-xl cursor-pointer hover:bg-surface-container-high transition-all border-2 border-dashed border-outline-variant hover:border-primary-container">
            <div className="w-16 h-16 bg-surface-container-highest rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined text-primary-container text-3xl">description</span>
            </div>
            <h3 className="text-lg font-bold font-headline text-primary mb-2">Content Word/Excel</h3>
            <p className="text-sm text-center text-on-surface-variant max-w-[240px]">
              {contentFile ? contentFile.name : "Upload the raw data or document containing your deck's narrative"}
            </p>
            {contentFile && (
              <button
                type="button"
                onClick={() => setContentFile(null)}
                className="mt-4 text-xs font-semibold text-primary-container hover:underline z-10"
              >
                Remove file
              </button>
            )}
            <input className="absolute inset-0 opacity-0 cursor-pointer" type="file" accept=".docx,.xlsx" onChange={handleFileChange('content')} />
          </div>
        </section>

        <section className="bg-surface-container-lowest p-8 rounded-xl shadow-sm border border-outline-variant/10 space-y-10">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-12">
            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">palette</span> Tone
              </h4>
              <div className="flex flex-col gap-3">
                {(['Executive', 'Formal', 'Concise'] as Tone[]).map((t) => (
                  <label key={t} className="flex items-center gap-3 cursor-pointer group">
                    <input
                      className="w-4 h-4 text-primary-container focus:ring-primary-container border-outline-variant"
                      name="tone"
                      type="radio"
                      value={t}
                      checked={tone === t}
                      onChange={() => setTone(t)}
                    />
                    <span className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors">{t}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">groups</span> Audience
              </h4>
              <div className="flex flex-col gap-3">
                {(['Management', 'Team', 'External'] as Audience[]).map((a) => (
                  <label key={a} className="flex items-center gap-3 cursor-pointer group">
                    <input
                      className="w-4 h-4 text-primary-container focus:ring-primary-container border-outline-variant"
                      name="audience"
                      type="radio"
                      value={a}
                      checked={audience === a}
                      onChange={() => setAudience(a)}
                    />
                    <span className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors">{a}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">straighten</span> Length
              </h4>
              <div className="flex flex-col gap-3">
                {(['5 slides', '10 slides', '15 slides'] as Length[]).map((l) => (
                  <label key={l} className="flex items-center gap-3 cursor-pointer group">
                    <input
                      className="w-4 h-4 text-primary-container focus:ring-primary-container border-outline-variant"
                      name="length"
                      type="radio"
                      value={l}
                      checked={length === l}
                      onChange={() => setLength(l)}
                    />
                    <span className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors">{l}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">psychology</span> AI Engine
              </h4>
              <div className="flex flex-col gap-3">
                {(['Bedrock', 'OpenAI'] as AIEngine[]).map((e) => (
                  <label key={e} className="flex items-center gap-3 cursor-pointer group">
                    <input
                      className="w-4 h-4 text-primary-container focus:ring-primary-container border-outline-variant"
                      name="ai"
                      type="radio"
                      value={e}
                      checked={aiEngine === e}
                      onChange={() => setAIEngine(e)}
                    />
                    <span className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors">{e}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="pt-8 flex flex-col items-center">
            <button
              onClick={handleGenerateClick}
              disabled={!canSubmit}
              className={`btn-gradient w-full md:w-auto min-w-[320px] text-white py-4 px-12 rounded-xl font-bold text-lg shadow-lg transition-all flex items-center justify-center gap-3 ${canSubmit ? 'hover:scale-[1.02] active:scale-95' : 'opacity-60 cursor-not-allowed'}`}
            >
              <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
              {isSubmitting ? 'Submitting...' : 'Generate PPT'}
            </button>
            <p className="mt-4 text-xs text-on-surface-variant flex items-center gap-1">
              <span className="material-symbols-outlined text-[10px]">info</span>
              Estimated processing time: 45-90 seconds
            </p>
            {isSubmitting && (
              <div className="mt-5 w-full max-w-md">
                <div className="h-2 rounded-full bg-surface-container-high overflow-hidden">
                  <div className="h-full bg-primary-container transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
                </div>
                <p className="mt-2 text-xs text-center text-on-surface-variant">Preparing upload and starting your job... {uploadProgress}%</p>
              </div>
            )}
            {errorMessage && (
              <div className="mt-5 w-full max-w-2xl rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {errorMessage}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
