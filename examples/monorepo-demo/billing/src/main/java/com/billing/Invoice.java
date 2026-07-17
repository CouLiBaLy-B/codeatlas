package com.billing;

/**
 * Facture émise par le service de facturation.
 */
public class Invoice {
    private double amount;

    public Invoice(double amount) {
        this.amount = amount;
    }

    /**
     * Montant TTC de la facture.
     */
    public double total() {
        return this.amount * 1.2;
    }
}
