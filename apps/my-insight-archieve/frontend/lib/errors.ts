export function isUnauthorizedError(error: Error) {
  const text = error.message.toLowerCase();
  return text.includes('unauthorized') || text.includes('401') || text.includes('forbidden');
}
