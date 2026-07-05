# Known Limitations

- Antivirus scanning is not implemented.
- Production SMS and push providers are not integrated.
- Production email depends on SMTP environment credentials.
- ML fraud scoring and advanced trust scoring are deferred.
- OpenTelemetry/metrics export is deferred until hosting target is selected.
- Multi-region deployment, Kubernetes, and autoscaling are deferred.
- Local Redis absence produces non-fatal realtime warnings.
# Wallet Recharge Provider Integration

Wallet recharge is currently a manual finance-review flow based on uploaded transfer receipts.
It does not yet reconcile directly against a bank or payment-provider webhook.
Future provider integration should preserve the current review, idempotency, and audit model.
