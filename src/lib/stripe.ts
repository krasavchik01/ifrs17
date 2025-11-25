import Stripe from 'stripe';

let stripeInstance: Stripe | null = null;

export function getStripe(): Stripe {
  if (!stripeInstance) {
    const apiKey = process.env.STRIPE_SECRET_KEY;
    if (!apiKey) {
      throw new Error('STRIPE_SECRET_KEY environment variable is not set');
    }
    stripeInstance = new Stripe(apiKey, {
      apiVersion: '2025-02-24.acacia',
      typescript: true,
    });
  }
  return stripeInstance;
}

// Export a lazy-loading proxy for backward compatibility
export const stripe = new Proxy({} as Stripe, {
  get: (_, prop) => {
    return (getStripe() as any)[prop];
  },
});

export const STRIPE_PLANS = {
  starter: {
    name: 'Starter',
    price: 49900, // $499 in cents
    currency: 'usd',
    interval: 'month' as const,
    features: [
      'До 1,000 контрактов',
      'Базовые расчеты IFRS 17',
      'Стандартная отчетность',
      'Email поддержка',
    ],
  },
  professional: {
    name: 'Professional',
    price: 149900, // $1,499 in cents
    currency: 'usd',
    interval: 'month' as const,
    features: [
      'До 10,000 контрактов',
      'Все расчеты IFRS 17',
      'Расширенная аналитика',
      'API интеграция',
      'Приоритетная поддержка',
    ],
  },
  enterprise: {
    name: 'Enterprise',
    price: 0, // Custom pricing
    currency: 'usd',
    interval: 'month' as const,
    features: [
      'Неограниченные контракты',
      'Кастомизация',
      'Dedicated infrastructure',
      'SLA 99.9%',
      'Персональный менеджер',
    ],
  },
};

/**
 * Create Stripe customer
 */
export async function createStripeCustomer(
  email: string,
  organizationName: string,
  organizationId: string
) {
  const customer = await stripe.customers.create({
    email,
    name: organizationName,
    metadata: {
      organizationId,
    },
  });

  return customer;
}

/**
 * Create subscription
 */
export async function createSubscription(
  customerId: string,
  priceId: string
) {
  const subscription = await stripe.subscriptions.create({
    customer: customerId,
    items: [{ price: priceId }],
    payment_behavior: 'default_incomplete',
    payment_settings: { save_default_payment_method: 'on_subscription' },
    expand: ['latest_invoice.payment_intent'],
  });

  return subscription;
}

/**
 * Cancel subscription
 */
export async function cancelSubscription(subscriptionId: string) {
  const subscription = await stripe.subscriptions.cancel(subscriptionId);
  return subscription;
}

/**
 * Update subscription
 */
export async function updateSubscription(
  subscriptionId: string,
  newPriceId: string
) {
  const subscription = await stripe.subscriptions.retrieve(subscriptionId);

  const updatedSubscription = await stripe.subscriptions.update(subscriptionId, {
    items: [
      {
        id: subscription.items.data[0].id,
        price: newPriceId,
      },
    ],
  });

  return updatedSubscription;
}

/**
 * Create Stripe Price for a plan
 */
export async function createPrice(
  planKey: keyof typeof STRIPE_PLANS,
  productId: string
) {
  const plan = STRIPE_PLANS[planKey];

  if (plan.price === 0) {
    // Enterprise is custom pricing
    return null;
  }

  const price = await stripe.prices.create({
    product: productId,
    unit_amount: plan.price,
    currency: plan.currency,
    recurring: {
      interval: plan.interval,
    },
    metadata: {
      plan: planKey,
    },
  });

  return price;
}

/**
 * Get or create product
 */
export async function getOrCreateProduct() {
  const products = await stripe.products.list({
    limit: 1,
  });

  if (products.data.length > 0) {
    return products.data[0];
  }

  const product = await stripe.products.create({
    name: 'IFRS 17 Pro Subscription',
    description: 'Professional IFRS 17 automation platform',
  });

  return product;
}

/**
 * Handle Stripe webhook events
 */
export async function handleStripeWebhook(
  event: Stripe.Event,
  prisma: any
) {
  switch (event.type) {
    case 'customer.subscription.created':
    case 'customer.subscription.updated': {
      const subscription = event.data.object as Stripe.Subscription;
      const customerId = subscription.customer as string;

      // Get organization by Stripe customer ID
      const organization = await prisma.organization.findUnique({
        where: { stripeCustomerId: customerId },
      });

      if (organization) {
        await prisma.organization.update({
          where: { id: organization.id },
          data: {
            stripeSubscriptionId: subscription.id,
            subscriptionStatus: subscription.status === 'active' ? 'active' : 'inactive',
          },
        });
      }
      break;
    }

    case 'customer.subscription.deleted': {
      const subscription = event.data.object as Stripe.Subscription;
      const customerId = subscription.customer as string;

      const organization = await prisma.organization.findUnique({
        where: { stripeCustomerId: customerId },
      });

      if (organization) {
        await prisma.organization.update({
          where: { id: organization.id },
          data: {
            subscriptionStatus: 'inactive',
          },
        });
      }
      break;
    }

    case 'invoice.payment_succeeded': {
      const invoice = event.data.object as Stripe.Invoice;
      // Handle successful payment
      console.log('Payment succeeded:', invoice.id);
      break;
    }

    case 'invoice.payment_failed': {
      const invoice = event.data.object as Stripe.Invoice;
      // Handle failed payment
      console.log('Payment failed:', invoice.id);
      break;
    }
  }
}
