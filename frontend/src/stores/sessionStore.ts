import { create } from 'zustand';

interface SessionStore {
  sessionToken: string;
}

// 초기화 로직 (앱 최상단에서 접근할 때 한 번 실행)
const getInitialToken = () => {
  const token = localStorage.getItem('sessionToken');
  if (token) return token;
  const newToken = crypto.randomUUID();
  localStorage.setItem('sessionToken', newToken);
  return newToken;
};

export const useSessionStore = create<SessionStore>(() => ({
  sessionToken: getInitialToken(),
}));
