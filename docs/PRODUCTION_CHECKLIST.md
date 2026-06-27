# Production Checklist

- [ ] `DJANGO_SECRET_KEY` set to strong non-placeholder value.
- [ ] `DEBUG=False`.
- [ ] `ALLOWED_HOSTS` contains production hosts only.
- [ ] `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` use HTTPS origins.
- [ ] PostgreSQL `DATABASE_URL` points to managed or backed-up instance.
- [ ] Redis URL configured for Channels/Celery.
- [ ] SMTP settings configured or transactional email explicitly deferred.
- [ ] Sentry DSN configured or monitoring exception accepted.
- [ ] Backups tested.
- [ ] Static files collected.
- [ ] Media storage configured and private-media policy reviewed.
- [ ] Nginx/TLS configured.
- [ ] Health/readiness checks monitored.
- [ ] Admin smoke tests passed.
- [ ] Rollback plan approved.
