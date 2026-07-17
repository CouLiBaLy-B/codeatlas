package com.shop;

/**
 * Produit dématérialisé : TVA réduite.
 */
public class DigitalProduct extends Product {
    private String downloadUrl;

    public DigitalProduct(String name, double price, String downloadUrl) {
        super(name, price);
        this.downloadUrl = downloadUrl;
    }

    /**
     * La TVA réduite s'applique aux biens numériques.
     */
    public double priceWithTax(double rate) {
        return super.priceWithTax(0.055);
    }
}
