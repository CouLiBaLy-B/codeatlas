/** Coquille applicative du front. */

/** Racine de l'interface. */
export class AppShell {
  title: string;

  constructor(title: string) {
    this.title = title;
  }

  /** Rend l'application. */
  render(): string {
    return `<main>${this.title}</main>`;
  }
}
