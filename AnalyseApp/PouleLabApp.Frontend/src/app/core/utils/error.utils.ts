export function extractErrorMessage(err: unknown, fallback = 'Une erreur est survenue.'): string {
  if (!err) return fallback;
  const e = err as any;
  if (e?.error?.message) return e.error.message;
  if (e?.error?.errors) {
    const messages = Object.values(e.error.errors).flat().filter(Boolean);
    if (messages.length > 0) return (messages as string[]).join(' ');
  }
  if (e?.error?.title) return e.error.title;
  if (e?.message) return e.message;
  if (e?.status) {
    const map: Record<number, string> = {
      400: 'Données invalides.',
      401: 'Non autorisé.',
      403: 'Accès refusé.',
      404: 'Ressource introuvable.',
      409: 'Conflit de données.',
      500: 'Erreur serveur. Veuillez réessayer.',
    };
    return map[e.status] ?? fallback;
  }
  return fallback;
}
