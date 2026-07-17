/** Service de catalogue au-dessus d'un dépôt. */

import { DigitalProduct, Product, ProductRepository } from '../models/product';

/** Expose le catalogue ; le dépôt est fourni par l'appelant. */
export class CatalogService {
  private repo: ProductRepository;

  constructor(repo: ProductRepository) {
    this.repo = repo;
  }

  /** Crée et enregistre un produit, numérique ou physique. */
  register(name: string, price: number, digital: boolean = false): Product {
    const product = digital
      ? new DigitalProduct(name, price, `https://dl.example/${name}`)
      : new Product(name, price);
    this.repo.save(product);
    return product;
  }

  find(name: string): Product | undefined {
    return this.repo.find(name);
  }
}

/** Formate l'étiquette d'un produit. */
export function formatLabel(product: Product): string {
  return `${product.name} — ${product.price} €`;
}
