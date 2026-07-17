/** Produits du catalogue (corpus TypeScript). */

/** Un produit physique du catalogue. */
export class Product {
  name: string;
  price: number;

  constructor(name: string, price: number) {
    this.name = name;
    this.price = price;
  }

  /** Prix TTC pour un taux donné. */
  priceWithTax(rate: number = 0.2): number {
    return this.rounded(this.price * (1 + rate));
  }

  private rounded(value: number): number {
    return Math.round(value * 100) / 100;
  }
}

/** Produit dématérialisé : TVA réduite. */
export class DigitalProduct extends Product {
  downloadUrl: string;

  constructor(name: string, price: number, downloadUrl: string) {
    super(name, price);
    this.downloadUrl = downloadUrl;
  }
}

/** Contrat de dépôt de produits. */
export interface ProductRepository {
  save(product: Product): void;
  find(name: string): Product | undefined;
}
