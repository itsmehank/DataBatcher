const API_BASE =
  typeof window === 'undefined'
    ? process.env.INTERNAL_API_BASE_URL || 'http://backend:4000/api'
    : process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:4000/api';

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    credentials: 'include',
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
