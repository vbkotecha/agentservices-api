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
retirement preparation. Their definitions are retained for historical reference
and should stay disabled.

## Completed hosting shutdown

The AgentServices Vercel production project has been paused. Verified:
`agentservices.to`, `api.agentservices.to`, the project's default Vercel domain,
and its active production deployment URL return `503 DEPLOYMENT_PAUSED`.
Preview deployments and production deployment URLs are restricted to Vercel
team authentication. New preview builds are disabled and automatic Git builds
are skipped. The project, domains and build history have not been deleted.

YappaCall and the separate operations dashboard's production deployment and
settings were verified unchanged. No external Stripe resources were modified.

## Finish the shutdown

1. Merge the AgentServices cleanup pull request. This repository also contains
   the separate operations dashboard: do not archive the entire shared
   repository without explicit confirmation. Preserve an AgentServices-only
   archive if the dashboard must remain maintained.
2. Keep the **agentservices-api** Vercel project paused, preview builds disabled,
   automatic Git builds skipped and deployment URL protection enabled. Its Git
   repository connection remains present; do not reconnect or re-enable builds
   as part of unrelated dashboard work. Do not disable **yappa-ops-dashboard**.
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
   longer publicly serve the application. Archive only the intended
   AgentServices source, without affecting maintenance of the shared dashboard.

Replit hosting shutdown, external Stripe cleanup and source archiving are still
separate operations. The completed Vercel pause above is not a claim that these
remaining steps have happened.