# AgentServices retirement

This project is being retired. Preserve the repository and financial records;
do not treat a code cleanup or repository archive as proof that hosting and
customer billing have stopped.

## Code cleanup

- Remove the Stripe-backed human billing door, checkout, webhook, credit tools,
  configuration, dependency, and discovery advertising.
- Keep the separate x402/USDC REST implementation in the archive.
- Paid MCP tools must not become free when the credit ledger is removed.
- Stop scheduled health checks and automatic MCP registry publication.

The GitHub health-check and MCP publishing workflows were disabled during
retirement preparation. Their definitions remain available for manual use,
but should stay disabled for an archived service.

## Finish the shutdown

1. Merge the cleanup pull request before archiving the GitHub repository.
2. In Vercel, take down the **agentservices-api** project serving
   `agentservices.to` and `api.agentservices.to`, including accessible deployment
   URLs. Disconnect its Git integration so pushes cannot redeploy it. Do not
   disable the separate **yappa-ops-dashboard** project.
3. In Replit's Publishing tool, shut down this project's public deployment.
   Stopping workspace development servers does not shut down a published app.
4. In the Stripe account that served this product, check for active subscriptions,
   pending payments and refunds. Cancel product-specific recurring billing as
   appropriate, disable its webhook endpoints/payment links, archive its
   products/prices, and revoke dedicated credentials. Keep transaction records;
   do not close a shared Stripe account or revoke keys used by other products.
   **Do not touch any YappaCall Stripe products, subscriptions, customers,
   webhooks, credentials, or account settings.** Only change resources whose
   AgentServices ownership has been verified; leave ambiguous/shared resources
   unchanged.
5. Remove this product's deployed credentials from its hosting settings after
   handling any outstanding billing. Code deletion does not revoke credentials
   or cancel subscriptions.
6. Remove or mark inactive external MCP/directory listings and decide whether to
   retain the domains or remove their hosting DNS records.
7. Verify the custom domains, Vercel deployment URLs and Replit published URL no
   longer serve the application. Then archive the GitHub repository.

Hosting shutdown, external Stripe cleanup and GitHub archiving are separate
operations. This document is a checklist, not a claim that those operations
have already happened.