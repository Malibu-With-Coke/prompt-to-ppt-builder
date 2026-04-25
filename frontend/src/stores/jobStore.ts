import { create } from 'zustand';

export type Tone = 'Executive' | 'Formal' | 'Concise';
export type Audience = 'Management' | 'Team' | 'External';
export type Length = '5 slides' | '10 slides' | '15 slides';
export type AIEngine = 'Bedrock' | 'OpenAI';

interface JobStore {
  currentJobId: string | null;
  setCurrentJobId: (id: string | null) => void;
  tone: Tone;
  setTone: (tone: Tone) => void;
  audience: Audience;
  setAudience: (audience: Audience) => void;
  length: Length;
  setLength: (length: Length) => void;
  aiEngine: AIEngine;
  setAIEngine: (aiEngine: AIEngine) => void;
}

export const useJobStore = create<JobStore>((set) => ({
  currentJobId: null,
  setCurrentJobId: (id) => set({ currentJobId: id }),
  tone: 'Executive',
  setTone: (tone) => set({ tone }),
  audience: 'Management',
  setAudience: (audience) => set({ audience }),
  length: '10 slides',
  setLength: (length) => set({ length }),
  aiEngine: 'Bedrock',
  setAIEngine: (aiEngine) => set({ aiEngine }),
}));
