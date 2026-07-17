package com.shop;

/**
 * Un produit physique du catalogue.
 */
public class Product {
    private String name;
    private double price;

    public Product(String name, double price) {
        this.name = name;
        this.price = price;
    }

    /**
     * Prix TTC pour un taux donné.
     */
    public double priceWithTax(double rate) {
        return this.price * (1 + rate);
    }

    public String getName() {
        return this.name;
    }

    private double rounded(double value) {
        return Math.round(value * 100.0) / 100.0;
    }
}
