const BASE = '/api/expert/experts';

const handleResponse = async (res: Response) => {
  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const body = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const message = isJson ? body?.message || 'Request failed' : body;
    throw new Error(message);
  }
  return body;
}

export const createRewriteExpert = async (data: any): Promise<any> => {
  const res = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
};

export const getRewriteExpertsList = async (): Promise<any> => {
  console.log('getRewriteExpertsList--->')
  const res = await fetch(BASE, { method: 'GET' });
  return handleResponse(res);
};

export const getRewriteExpertById = async (expertId: number): Promise<any> => {
  const res = await fetch(`${BASE}/${expertId}`, { method: 'GET' });
  return handleResponse(res);
};

export const updateRewriteExpert = async (data: any): Promise<any> => {
  const res = await fetch(`${BASE}/${data.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
};

export const patchRewriteExpert = async (expertId: number, data: any): Promise<any> => {
  const res = await fetch(`${BASE}/${expertId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
};

export const deleteRewriteExpert = async (expertId: number): Promise<any> => {
  const res = await fetch(`${BASE}/${expertId}`, { method: 'DELETE' });
  return handleResponse(res);
};