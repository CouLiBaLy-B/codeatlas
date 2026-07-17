/** Utilitaires partagés entre services. */

/** Formate un prix en euros. */
export function formatPrice(amount: number): string {
  return `${amount.toFixed(2)} €`;
}
