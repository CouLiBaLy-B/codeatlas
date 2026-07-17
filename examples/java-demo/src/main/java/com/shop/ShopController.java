package com.shop;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Contrôleur HTTP de la boutique (routes Spring factices).
 */
@RestController
public class ShopController {
    private CatalogService catalog = new CatalogService();

    /**
     * Liste les produits.
     */
    @GetMapping("/products")
    public String listProducts() {
        return "[]";
    }

    @PostMapping("/products")
    public String createProduct(String name, double price) {
        this.catalog.register(new Product(name, price));
        return name;
    }
}
