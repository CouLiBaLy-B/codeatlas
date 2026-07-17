package com.shop;

/**
 * Point d'entrée de l'application.
 */
public class Application {
    public static void main(String[] args) {
        CatalogService catalog = new CatalogService();
        catalog.register(new Product("clavier", 49.9));
        System.out.println(catalog.find("clavier").getName());
    }
}
