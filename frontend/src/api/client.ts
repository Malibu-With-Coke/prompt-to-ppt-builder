import axios from 'axios';

export const ensureSessionToken = () => {
  const existingToken = localStorage.getItem('sessionToken');
  if (existingToken) {
    return existingToken;
  }

  const nextToken = crypto.randomUUID();
  localStorage.setItem('sessionToken', nextToken);
  return nextToken;
};

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

axiosInstance.interceptors.request.use((config) => {
  const token = ensureSessionToken();
  config.headers = config.headers ?? {};
  config.headers['X-Session-Token'] = token;
  return config;
});

export default axiosInstance;