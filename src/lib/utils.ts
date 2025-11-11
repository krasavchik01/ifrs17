import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format currency for Kazakhstan
export function formatCurrency(amount: number, currency: string = 'KZT'): string {
  return new Intl.NumberFormat('ru-KZ', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

// Format date
export function formatDate(date: Date | string): string {
  return new Intl.DateTimeFormat('ru-KZ', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(date));
}

// Calculate discount factor
export function calculateDiscountFactor(rate: number, periods: number): number {
  return Math.pow(1 + rate, -periods);
}

// Calculate present value
export function calculatePresentValue(
  cashFlow: number,
  discountRate: number,
  periods: number
): number {
  return cashFlow * calculateDiscountFactor(discountRate, periods);
}

// Calculate NPV
export function calculateNPV(cashFlows: number[], discountRate: number): number {
  return cashFlows.reduce((npv, cf, period) => {
    return npv + calculatePresentValue(cf, discountRate, period);
  }, 0);
}

// Generate random string for IDs
export function generateId(prefix: string = '', length: number = 16): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = prefix;
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}
