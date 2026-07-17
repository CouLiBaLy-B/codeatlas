package com.shop;

/**
 * Contrat du catalogue de produits.
 */
public interface Catalog {
    void register(Product product);

    Product find(String name);
}
