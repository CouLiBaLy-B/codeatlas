/** Coquille applicative du front. */

import { formatPrice } from 'shared-lib';

/** Racine de l'interface. */
export class AppShell {
  title: string;

  constructor(title: string) {
    this.title = title;
  }

  /** Rend l'application. */
  render(): string {
    return `<main>${this.title} — ${formatPrice(9.9)}</main>`;
  }
}
