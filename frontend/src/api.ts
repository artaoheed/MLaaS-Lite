import axios from 'axios';

const API_URL = 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
});

// Types based on your Backend Models
export interface Job {
  id: number;
  team_id: number;
  status: string;
  argo_workflow_name: string;
}

export const fetchJobs = async () => {
    // We haven't built GET /jobs yet, but we will next!
    const response = await api.get<Job[]>('/jobs'); 
    return response.data;
};

export const submitJob = async (teamName: string, code: string) => {
  const response = await api.post('/jobs', {
    team_name: teamName,
    python_code: code
  });
  return response.data;
};

export interface Model {
  id: number;
  name: string;
  s3_path: string;
  created_at: string;
}

export const fetchModels = async () => {
  const response = await api.get<Model[]>('/models');
  return response.data;
};

export const deployModel = async (modelId: number) => {
  const response = await api.post('/deployments', { model_id: modelId });
  return response.data;
};
