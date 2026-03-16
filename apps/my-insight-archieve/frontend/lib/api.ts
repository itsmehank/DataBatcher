const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:4000/api';

export function getToken() {
  if (typeof window === 'undefined') {
    return '';
  }
  return localStorage.getItem('accessToken') || '';
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
    cache: 'no-store',
  });

  if (!res.ok) {
    let detail = '요청에 실패했습니다.';
    try {
      const body = (await res.json()) as { message?: string | string[] };
      if (Array.isArray(body.message)) {
        detail = body.message.join(', ');
      } else if (body.message) {
        detail = body.message;
      }
    } catch {
      detail = `${res.status} ${res.statusText}`;
    }
    throw new Error(detail);
  }

  return (await res.json()) as T;
}
