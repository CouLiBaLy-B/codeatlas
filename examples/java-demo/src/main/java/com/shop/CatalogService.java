package com.shop;

import java.util.HashMap;
import java.util.Map;

import com.shop.Product;

/**
 * Catalogue en mémoire.
 */
public class CatalogService implements Catalog {
    private Map<String, Product> items = new HashMap<>();

    /**
     * Enregistre ou remplace un produit.
     */
    public void register(Product product) {
        this.items.put(product.getName(), product);
    }

    public Product find(String name) {
        if (this.items.containsKey(name)) {
            return this.items.get(name);
        }
        return null;
    }
}
